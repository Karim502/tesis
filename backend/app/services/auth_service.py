"""Lógica de negocio de autenticación (independiente de HTTP)."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import Usuario


class InvalidCredentials(Exception):
    pass


class InactiveUser(Exception):
    pass


def authenticate(db: Session, email: str, password: str) -> Usuario:
    email_norm = email.strip().lower()
    user = db.execute(select(Usuario).where(Usuario.email == email_norm)).scalar_one_or_none()

    # Se verifica la contraseña SIEMPRE (con hash falso si no hay usuario) para igualar tiempos.
    password_ok = verify_password(password, user.password_hash if user else None)

    # Mismo error para "correo inexistente" y "contraseña errónea": evita enumerar cuentas.
    if user is None or not password_ok:
        raise InvalidCredentials()

    # El estado "inactivo" solo se revela a quien ya demostró conocer la contraseña.
    if not user.activo:
        raise InactiveUser()

    user.ultimo_login = datetime.now(timezone.utc)
    db.commit()
    return user
