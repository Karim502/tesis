"""Endpoints de sesión: login, logout y usuario actual."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import Usuario
from app.schemas.auth import LoginRequest, UserOut
from app.services.auth_service import InactiveUser, InvalidCredentials, authenticate

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = dict(
    httponly=True,                   # inaccesible desde JS (anti-XSS)
    secure=settings.COOKIE_SECURE,   # solo por HTTPS en producción
    samesite="lax",                  # no se envía en POST cross-site (anti-CSRF)
    path="/",
)


@router.post("/login", response_model=UserOut)
@limiter.limit("5/minute")  # máx. 5 intentos por minuto por IP
def login(request: Request, response: Response, data: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = authenticate(db, data.email, data.password)
    except InvalidCredentials:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales inválidas"},
        )
    except InactiveUser:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "INACTIVE_USER", "message": "Usuario inactivo"},
        )

    token = create_access_token(user.id, user.rol.value)
    response.set_cookie(
        settings.COOKIE_NAME, token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, **_COOKIE_OPTS
    )
    response.headers["Cache-Control"] = "no-store"  # ningún proxy/navegador cachea la respuesta
    # El token NO se devuelve en el cuerpo JSON: solo viaja en la cookie HttpOnly.
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(settings.COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: Usuario = Depends(get_current_user)):
    """El frontend lo usa al cargar para recuperar la sesión sin leer el token."""
    return user
