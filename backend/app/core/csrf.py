"""Defensa en profundidad contra CSRF para acciones destructivas (se suma al SameSite de la cookie)."""
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

from app.core.config import settings

_SEGUROS = {"GET", "HEAD", "OPTIONS"}


def _extraer_origen(valor: str | None) -> str | None:
    if not valor:
        return None
    limpio = valor.strip().rstrip("/")
    if not limpio:
        return None
    if limpio.lower() == "null":
        return "null"
    partes = urlsplit(limpio)
    if partes.scheme and partes.netloc:
        return f"{partes.scheme}://{partes.netloc}"
    return limpio


def verificar_origen(request: Request) -> None:
    """
    En peticiones que modifican datos, valida que Origin (o Referer como respaldo)
    pertenezca a CORS_ORIGINS. En producción, si viaja la cookie de sesión (SameSite=None),
    también exige que uno de esos encabezados esté presente.
    """
    if request.method in _SEGUROS:
        return

    origen = _extraer_origen(request.headers.get("origin"))
    if origen is None:
        origen = _extraer_origen(request.headers.get("referer"))

    if origen is not None:
        if origen not in settings.CORS_ORIGINS:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={"code": "BAD_ORIGIN", "message": "Origen no permitido"},
            )
        return

    if settings.ENV == "prod" and settings.COOKIE_NAME in request.cookies:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "BAD_ORIGIN", "message": "Origen requerido para sesiones autenticadas"},
        )