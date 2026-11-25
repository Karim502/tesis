import hashlib, logging, os, tempfile, threading, time, uuid
from functools import lru_cache
from pathlib import Path
from app.core.config import settings

log = logging.getLogger(__name__)
_descarga = threading.Lock()

class AlmacenamientoError(Exception):
    """Mensaje seguro para mostrar (sin claves, rutas ni respuesta cruda del proveedor)."""

def _errores_transferencia() -> tuple:
    # upload_file/download_file envuelven los errores de red en estas dos, que NO heredan de ClientError
    from boto3.exceptions import S3TransferFailedError, S3UploadFailedError
    from botocore.exceptions import BotoCoreError, ClientError
    return BotoCoreError, ClientError, S3UploadFailedError, S3TransferFailedError

def usa_s3() -> bool:
    return settings.STORAGE_BACKEND == "s3"

def carpeta_local() -> Path:           # MODELS_DIR (local) o caché temporal (s3)
    if usa_s3():
        return Path(settings.MODELS_CACHE_DIR) if settings.MODELS_CACHE_DIR else Path(tempfile.gettempdir()) / "modelos_cache"
    from app.services.explicabilidad import RAIZ_BACKEND
    p = Path(settings.MODELS_DIR)
    return p if p.is_absolute() else RAIZ_BACKEND / p

def _clave(nombre: str) -> str:        # solo el NOMBRE: la clave no puede salir del prefijo
    return f"{settings.S3_PREFIX.strip('/')}/{Path(nombre).name}".lstrip("/")

@lru_cache(maxsize=1)
def _cliente():
    import boto3
    from botocore.config import Config
    kw = {}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kw = dict(aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY.get_secret_value())
    return boto3.client(
        "s3", region_name=settings.S3_REGION, endpoint_url=settings.S3_ENDPOINT_URL or None,
        config=Config(signature_version="s3v4",
                      s3={"addressing_style": "path" if settings.S3_ENDPOINT_URL else "auto"},  # Supabase/R2/MinIO
                      retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=5, read_timeout=60),
        **kw)

def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

# ── SUBIR (al terminar de entrenar)
def publicar(ruta_local: Path, sha256: str) -> None:
    if not usa_s3():
        return
    clave = _clave(ruta_local.name)
    try:
        c = _cliente()
        c.upload_file(str(ruta_local), settings.S3_BUCKET_NAME, clave, ExtraArgs={"Metadata": {"sha256": sha256}})
        remoto = c.head_object(Bucket=settings.S3_BUCKET_NAME, Key=clave)["ContentLength"]
    except _errores_transferencia():
        log.exception("No se pudo subir %s al bucket", clave)
        raise AlmacenamientoError("No se pudo subir el modelo al almacenamiento (revisa el bucket y las credenciales).") from None
    if remoto != ruta_local.stat().st_size:
        raise AlmacenamientoError("El modelo subido no coincide en tamaño con el local; se descarta.")

# ── BAJAR (al arrancar o al activar)
def asegurar_local(nombre: str, sha256: str | None) -> Path:
    destino = carpeta_local() / Path(nombre).name
    if destino.is_file() or not usa_s3():
        return destino
    with _descarga:
        if destino.is_file():
            return destino
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_name(f".{destino.name}.{uuid.uuid4().hex}.tmp")
        try:
            _cliente().download_file(settings.S3_BUCKET_NAME, _clave(nombre), str(tmp))
            if sha256 and _sha256(tmp) != sha256:
                raise AlmacenamientoError("El archivo descargado no coincide con la huella registrada; se rechaza.")
            os.replace(tmp, destino)   # atómico
        except _errores_transferencia():
            log.exception("No se pudo descargar %s del bucket", _clave(nombre))
            raise AlmacenamientoError("No se pudo descargar el modelo del almacenamiento.") from None
        finally:
            tmp.unlink(missing_ok=True)
    return destino