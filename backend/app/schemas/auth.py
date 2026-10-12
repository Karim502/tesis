"""Esquemas Pydantic: validan y limitan toda entrada antes de tocar la base de datos."""
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.user import Rol


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if not v:
            raise ValueError("La contraseña es obligatoria")
        # bcrypt solo procesa 72 bytes; limitar también evita payloads enormes (DoS).
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña excede el máximo permitido")
        return v


class UserOut(BaseModel):
    """Datos públicos del usuario. Nótese que NO incluye password_hash."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: EmailStr
    rol: Rol
