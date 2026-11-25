"""
Registra un modelo .joblib como versión ACTIVA inicial (versión 1) para poblar métricas en el panel.
Uso (desde /backend):
  python -m scripts.registrar_modelo_inicial --archivo modelo_ganador.joblib --accuracy 0.91 --f1 0.88
"""
import argparse
import shutil
from pathlib import Path

import app.models.user  # noqa: F401 - registra el modelo Usuario en metadata SQLAlchemy
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.model_version import EstadoModelo, ModelVersion
from app.services import modelos


def _validar_metrica(valor: float | None, nombre: str) -> None:
    if valor is not None and not (0.0 <= valor <= 1.0):
        raise SystemExit(f"Error: --{nombre} debe estar entre 0.0 y 1.0 (recibido: {valor}).")


def _resolver_origen(archivo: str, carpeta: Path) -> Path:
    ruta = Path(archivo)
    if ruta.is_file():
        return ruta
    en_carpeta = carpeta / archivo
    if en_carpeta.is_file():
        return en_carpeta
    raise SystemExit(f"No se encontró el archivo del modelo: {archivo} (ni en {carpeta}).")


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--archivo", required=True, help="Ruta al .joblib o nombre dentro de MODELS_DIR")
    a.add_argument("--accuracy", type=float, required=True)
    a.add_argument("--f1", type=float, required=True)
    a.add_argument("--precision", type=float)
    a.add_argument("--recall", type=float)
    a.add_argument("--roc-auc", type=float)
    args = a.parse_args()

    for nombre, valor in [
        ("accuracy", args.accuracy),
        ("f1", args.f1),
        ("precision", args.precision),
        ("recall", args.recall),
        ("roc-auc", args.roc_auc),
    ]:
        _validar_metrica(valor, nombre)

    carpeta = modelos.carpeta_modelos()
    carpeta.mkdir(parents=True, exist_ok=True)
    origen = _resolver_origen(args.archivo, carpeta)
    destino = carpeta / "modelo_v1.joblib"

    if origen.resolve() != destino.resolve():
        shutil.copyfile(origen, destino)

    with SessionLocal() as db:
        if db.execute(select(func.count()).select_from(ModelVersion)).scalar_one():
            raise SystemExit("Ya hay versiones registradas; usa el panel para activar o reentrenar.")
        v = ModelVersion(
            version=1,
            archivo=destino.name,
            estado=EstadoModelo.CANDIDATO.value,
            origen_datos="modelo inicial de la tesis",
            accuracy=args.accuracy,
            f1_score=args.f1,
            precision=args.precision,
            recall=args.recall,
            roc_auc=args.roc_auc,
            sha256=modelos.sha256_de(destino),
        )
        db.add(v)
        db.flush()
        for adv in modelos.activar(db, v, None):
            print("ADVERTENCIA:", adv)
        db.commit()

    print("Modelo inicial registrado y activo (versión 1).")
    if settings.STORAGE_BACKEND == "s3":
        print(
            "AVISO: STORAGE_BACKEND=s3 está activo. Verifica que "
            f"'{settings.S3_PREFIX}{destino.name}' esté subido al bucket '{settings.S3_BUCKET_NAME}'."
        )


if __name__ == "__main__":
    main()