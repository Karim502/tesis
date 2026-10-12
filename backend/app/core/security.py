"""Primitivas criptográficas: hashing de contraseñas (bcrypt) y JWT."""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

BCRYPT_ROUNDS = 12  # costo adaptativo: cada +1 duplica el tiempo de cálculo

# Hash falso calculado una sola vez. Se usa cuando el correo no existe, para que el
# tiempo de respuesta sea igual que con un usuario real (evita enumeración por timing).
_DUMMY_HASH = bcrypt.hashpw(b"contrasena-falsa", bcrypt.gensalt(BCRYPT_ROUNDS)).decode()


def hash_password(plain: str) -> str:
    """Bcrypt aplica un salt aleatorio por contraseña, embebido en el propio hash."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    """Comparación en tiempo constante. Sin hash real (usuario inexistente) valida contra el falso y devuelve False."""
    try:
        matches = bcrypt.checkpw(plain.encode("utf-8"), (hashed or _DUMMY_HASH).encode("utf-8"))
    except ValueError:  # hash malformado o contraseña > 72 bytes
        return False
    return matches and hashed is not None


def create_access_token(user_id: int, rol: str) -> str:
    """
    El payload lleva lo mínimo: id, rol y tiempos. NUNCA correo, contraseña ni datos
    sensibles: un JWT está firmado (íntegro) pero NO cifrado (cualquiera puede leerlo).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": rol,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),  # vida corta
        "jti": uuid.uuid4().hex,  # id único: permitirá revocar tokens individuales a futuro
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Lanza jwt.PyJWTError si el token está vencido, alterado o incompleto."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],  # lista blanca explícita
        options={"require": ["exp", "iat", "sub", "role"]},
    )
