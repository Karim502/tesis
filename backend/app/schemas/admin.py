"""Esquemas del módulo Administrador."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def _validar_password(v: str) -> str:
    # bcrypt solo usa los primeros 72 BYTES: se rechaza más largo en vez de truncar en silencio.
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes")
    if len(v) < 10:
        raise ValueError("La contraseña debe tener al menos 10 caracteres")
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("La contraseña debe combinar letras y números")
    return v


def _nombre(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("El nombre no puede estar vacío")
    return v


class AuditorCreate(BaseModel):
    nombre: str = Field(max_length=120)
    email: EmailStr
    password: str = Field(max_length=200)

    @field_validator("nombre")
    @classmethod
    def _n(cls, v: str) -> str:
        return _nombre(v)

    @field_validator("password")
    @classmethod
    def _p(cls, v: str) -> str:
        return _validar_password(v)

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v


class AuditorPatch(BaseModel):
    """Parcial: solo se aplica lo que viene en el cuerpo. `activo=false` SUSPENDE el acceso al instante."""
    nombre: str | None = Field(None, max_length=120)
    activo: bool | None = None
    password: str | None = Field(None, max_length=200)

    @field_validator("nombre")
    @classmethod
    def _n(cls, v):
        return None if v is None else _nombre(v)

    @field_validator("password")
    @classmethod
    def _p(cls, v):
        return None if v is None else _validar_password(v)

    @model_validator(mode="after")
    def _alguno(self):
        if not self.model_fields_set:
            raise ValueError("Envía al menos un campo a modificar")
        if any(getattr(self, c) is None for c in self.model_fields_set):
            raise ValueError("Los campos enviados no pueden ser null")
        return self


class AuditorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    email: str
    activo: bool
    ultimo_login: datetime | None
    creado_en: datetime
    revisiones: int = 0   # evaluaciones donde figura como último auditor


class AuditoresPage(BaseModel):
    items: list[AuditorOut]
    total: int
    limit: int
    offset: int


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    creado_en: datetime
    usuario_id: int | None
    usuario_email: str | None
    usuario_rol: str | None
    accion: str
    recurso_tipo: str | None
    recurso_id: int | None
    detalle: dict | None
    ip: str | None


class LogsPage(BaseModel):
    items: list[LogOut]
    total: int
    limit: int
    offset: int


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int
    archivo: str
    estado: Literal["ENTRENANDO", "CANDIDATO", "ACTIVO", "ARCHIVADO", "FALLIDO"]
    etapa: str | None
    accuracy: float | None
    f1_score: float | None
    precision: float | None
    recall: float | None
    roc_auc: float | None
    n_filas_train: int | None
    n_filas_test: int | None
    origen_datos: str | None
    sha256: str | None
    error: str | None
    iniciado_por: int | None
    creado_en: datetime
    finalizado_en: datetime | None
    activado_en: datetime | None


class ModelosOut(BaseModel):
    activo: ModelVersionOut | None
    versiones: list[ModelVersionOut]
    entrenando: bool
    modelo_en_uso: str    # "version" | "archivo_base": qué está sirviendo la API (ver README)


class ActivacionOut(BaseModel):
    modelo: ModelVersionOut
    advertencias: list[str]


class ServicioHealth(BaseModel):
    nombre: str
    estado: Literal["ok", "advertencia", "error"]
    detalle: str
    latencia_ms: float | None = None


class HealthOut(BaseModel):
    estado_general: Literal["ok", "advertencia", "error"]
    revisado_en: datetime
    servicios: list[ServicioHealth]
