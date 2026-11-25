"""Defensa en profundidad contra CSRF para acciones destructivas (se suma al SameSite de la cookie)."""
from fastapi import HTTPException, Request, status

from app.core.config import settings

_SEGUROS = {"GET", "HEAD", "OPTIONS"}


def verificar_origen(request: Request) -> None:
    """
    En peticiones que modifican datos, si el navegador envía `Origin` debe ser uno de CORS_ORIGINS.
    Si la cookie de sesión algún día se configura con SameSite=None (frontend y API en dominios distintos), esto
    impide que otra página haga DELETE/POST con la sesión del administrador. Clientes sin navegador (curl, scripts)
    no envían Origin y no son vector de CSRF.
    """
    if request.method in _SEGUROS:
        return
    origen = request.headers.get("origin")
    if origen and origen not in settings.CORS_ORIGINS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "BAD_ORIGIN", "message": "Origen no permitido"})
