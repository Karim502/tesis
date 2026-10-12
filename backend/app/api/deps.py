"""Dependencias de seguridad: autenticación (¿quién eres?) y autorización (¿qué puedes hacer?)."""
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import Rol, Usuario

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "NOT_AUTHENTICATED", "message": "Sesión no válida o expirada"},
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    # El token viaja en una cookie HttpOnly: el JavaScript del navegador no puede leerla,
    # así que un ataque XSS no puede robarlo (a diferencia de localStorage).
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise _UNAUTHORIZED
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise _UNAUTHORIZED

    # Se consulta la BD en cada petición: si el admin desactiva al usuario o cambia su rol,
    # el efecto es inmediato y no depende de lo que diga un token antiguo.
    user = db.get(Usuario, user_id)
    if user is None or not user.activo:
        raise _UNAUTHORIZED
    return user


def require_roles(*roles: Rol):
    """Fábrica de guards RBAC. Esta es la barrera REAL; los guards de React solo mejoran la UX."""

    def checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "No tienes permiso para este recurso"},
            )
        return user

    return checker
