"""
Registra tu modelo actual (p. ej. models/modelo_ganador.joblib) como versión ACTIVA para que el panel muestre sus métricas.
Uso (desde /backend):  python -m scripts.registrar_modelo_inicial --archivo modelo_ganador.joblib --accuracy 0.91 --f1 0.88
Copia el archivo a la carpeta de modelos con el nombre modelo_v1.joblib (o conserva el nombre que indiques).
Las métricas son las que obtuviste en tu tesis: aquí solo se registran, no se recalculan.
"""
import argparse
import shutil
import app.models.user

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.model_version import EstadoModelo, ModelVersion
from app.services import modelos


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--archivo", required=True, help="Nombre del .joblib dentro de la carpeta de modelos (o ruta a copiar)")
    a.add_argument("--accuracy", type=float, required=True)
    a.add_argument("--f1", type=float, required=True)
    a.add_argument("--precision", type=float)
    a.add_argument("--recall", type=float)
    a.add_argument("--roc-auc", type=float)
    args = a.parse_args()

    carpeta = modelos.carpeta_modelos()
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / "modelo_v1.joblib"
    origen = carpeta / args.archivo if not args.archivo.startswith(("/", ".")) else None
    if origen is not None and origen.is_file():
        if origen != destino:
            shutil.copyfile(origen, destino)
    else:
        shutil.copyfile(args.archivo, destino)

    with SessionLocal() as db:
        if db.execute(select(func.count()).select_from(ModelVersion)).scalar_one():
            raise SystemExit("Ya hay versiones registradas; usa el panel para activar o reentrenar.")
        v = ModelVersion(
            version=1, archivo=destino.name, estado=EstadoModelo.CANDIDATO.value, origen_datos="modelo inicial de la tesis",
            accuracy=args.accuracy, f1_score=args.f1, precision=args.precision, recall=args.recall, roc_auc=args.roc_auc,
            sha256=modelos.sha256_de(destino),
        )
        db.add(v)
        db.flush()
        for adv in modelos.activar(db, v, None):
            print("ADVERTENCIA:", adv)
        db.commit()
    print("Modelo inicial registrado y activo (versión 1).")


if __name__ == "__main__":
    main()
