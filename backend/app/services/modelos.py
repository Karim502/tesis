"""Registro de versiones del modelo: cuál está activo, cómo se activa y cómo se recupera de un cierre brusco."""
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.model_version import EstadoModelo, ModelVersion
from app.services.cuestionario import PREGUNTAS
from app.services.explicabilidad import RAIZ_BACKEND, ModeloNoDisponible, cargar_modelo_de

log = logging.getLogger(__name__)


class ActivacionInvalida(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def carpeta_modelos() -> Path:
    p = Path(settings.MODELS_DIR)
    return p if p.is_absolute() else RAIZ_BACKEND / p


def ruta_de(v: ModelVersion) -> Path:
    # Solo el NOMBRE del archivo: aunque la BD contuviera "../../etc/x", jamás se sale de la carpeta de modelos.
    return carpeta_modelos() / Path(v.archivo).name


def sha256_de(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


# ------------------------------------------------------------ modelo activo (consultado por SHAP en cada petición)
_TTL_S = 15  # con varios workers, otro proceso notaría una activación en <= 15 s
_cache: dict = {"hasta": 0.0, "ruta": None}


def invalidar_cache() -> None:
    _cache["hasta"] = 0.0


def ruta_activa() -> Path | None:
    ahora = time.monotonic()
    if ahora < _cache["hasta"]:
        return _cache["ruta"]
    ruta = None
    try:
        with SessionLocal() as db:
            v = db.execute(select(ModelVersion).where(ModelVersion.estado == EstadoModelo.ACTIVO.value)).scalar_one_or_none()
            ruta = ruta_de(v) if v else None
    except Exception:  # si la BD falla, se sigue con MODELO_PATH en vez de tumbar la explicabilidad
        log.exception("No se pudo consultar el modelo activo")
    _cache.update(hasta=ahora + _TTL_S, ruta=ruta)
    return ruta


def version_activa(db: Session) -> ModelVersion | None:
    return db.execute(select(ModelVersion).where(ModelVersion.estado == EstadoModelo.ACTIVO.value)).scalar_one_or_none()


# ------------------------------------------------------------ activación / rollback
def activar(db: Session, v: ModelVersion, admin_id: int | None) -> list[str]:
    """
    Pone `v` como modelo activo (sirve también para volver a una versión anterior). Antes de cambiar nada comprueba que
    el archivo exista, no haya sido alterado y se pueda cargar: nunca se activa un modelo que luego falle en producción.
    Devuelve advertencias (no bloqueantes). NO hace commit: lo hace el llamador junto con la bitácora.
    """
    if v.estado not in (EstadoModelo.CANDIDATO.value, EstadoModelo.ARCHIVADO.value, EstadoModelo.ACTIVO.value):
        raise ActivacionInvalida("INVALID_STATE", f"Una versión en estado {v.estado} no se puede activar.")
    ruta = ruta_de(v)
    if not ruta.is_file():
        raise ActivacionInvalida("MODEL_FILE_MISSING", "El archivo de esta versión ya no existe en el servidor.")
    if v.sha256 and sha256_de(ruta) != v.sha256:
        raise ActivacionInvalida("MODEL_FILE_ALTERED", "El archivo no coincide con la huella registrada; no se activará.")
    try:
        cargado = cargar_modelo_de(ruta, ruta.stat().st_mtime_ns)
    except ModeloNoDisponible as exc:
        raise ActivacionInvalida("MODEL_NOT_LOADABLE", f"El modelo no se pudo cargar ({exc.motivo}).") from exc

# Advertencia: columnas que el cuestionario ni el pipeline de features producen => SHAP respondería FEATURES_MISSING.
    conocidas = {p["id"] for p in PREGUNTAS} | {
        "regimen",
        "sector_economico",
        "emite_comprobantes",
        "ingresos_mensuales",
    }
    ajenas = [c for c in cargado.columnas if c not in conocidas]
    advertencias = []
    if ajenas:
        advertencias.append(
            "El modelo usa columnas que el cuestionario no recoge (" + ", ".join(ajenas) + "): "
            "revisa construir_features o la explicabilidad fallará."
        )

    ahora = datetime.now(timezone.utc)
    if v.estado != EstadoModelo.ACTIVO.value:
        db.execute(  # el índice único parcial exige liberar al anterior ANTES de activar el nuevo
            update(ModelVersion).where(ModelVersion.estado == EstadoModelo.ACTIVO.value).values(estado=EstadoModelo.ARCHIVADO.value)
        )
        db.flush()
        v.estado = EstadoModelo.ACTIVO.value
        v.activado_en, v.activado_por = ahora, admin_id
        db.flush()
    invalidar_cache()
    return advertencias


# ------------------------------------------------------------ recuperación
def marcar_huerfanos(db: Session, *, todos: bool = False) -> int:
    """
    Un entrenamiento vive en un hilo del servidor: si Render reinicia el proceso, la fila quedaría en ENTRENANDO para siempre
    (y, por el índice único, bloquearía nuevos entrenamientos). Se marcan FALLIDO los vencidos (o todos, al arrancar).
    """
    limite = datetime.now(timezone.utc) - timedelta(minutes=settings.ENTRENAMIENTO_TIMEOUT_MIN)
    cond = [ModelVersion.estado == EstadoModelo.ENTRENANDO.value]
    if not todos:
        cond.append(ModelVersion.creado_en < limite)
    r = db.execute(
        update(ModelVersion).where(*cond).values(
            estado=EstadoModelo.FALLIDO.value, etapa=None, finalizado_en=datetime.now(timezone.utc),
            error="El entrenamiento se interrumpió (reinicio o tiempo agotado del servidor).",
        )
    )
    db.commit()
    return r.rowcount or 0
