"""Configuración centralizada. Los secretos vienen del entorno (.env), nunca del código."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="forbid" hace que cualquier variable mal escrita en .env falle al arrancar
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    # --- Entorno ---
    ENV: Literal["dev", "prod"] = "dev"

    # --- Base de datos y Seguridad ---
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    GUEST_RATE_LIMIT: str = "30/hour"

    # --- Modelos, Explicabilidad y Reentrenamiento (MLOps) ---
    MODELS_DIR: str = "models"
    MODELO_PATH: str = "ml_models/modelo_ganador.joblib"
    MODELO_CLASE_RIESGO: str = "1"
    SECTOR_MUESTRA_MINIMA: int = Field(default=5, gt=0)

    ENTRENAMIENTO_CSV_PATH: str = "data/dataset_entrenamiento.csv"
    ENTRENAMIENTO_TARGET: str = "riesgo"
    ENTRENAMIENTO_FEATURES: list[str] | None = None
    ENTRENAMIENTO_MAX_MB: int = Field(default=5, gt=0)
    ENTRENAMIENTO_MIN_FILAS: int = Field(default=60, gt=0)
    ENTRENAMIENTO_TIMEOUT_MIN: int = Field(default=60, gt=0)

    # --- Almacenamiento S3 (MLOps) ---
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    S3_BUCKET_NAME: str | None = None
    S3_PREFIX: str = "models/"
    S3_REGION: str | None = None
    S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: SecretStr | None = None
    MODELS_CACHE_DIR: str | None = None

    @field_validator("DATABASE_URL")
    @classmethod
    def normalizar_database_url(cls, v: str) -> str:
        limpio = v.strip()
        if not limpio:
            raise ValueError("DATABASE_URL no puede estar vacío")
        if limpio.startswith("postgres://"):
            limpio = "postgresql://" + limpio[len("postgres://"):]
        return limpio

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def secret_must_be_strong(cls, v: str) -> str:
        limpio = v.strip()
        if len(limpio) < 32 or len(set(limpio)) < 8:
            raise ValueError("JWT_SECRET_KEY debe tener al menos 32 caracteres con suficiente entropía")
        return limpio

    @field_validator("CORS_ORIGINS")
    @classmethod
    def normalizar_cors_origins(cls, v: list[str]) -> list[str]:
        limpios = [o.strip().rstrip("/") for o in v if o and o.strip()]
        if not limpios:
            raise ValueError("CORS_ORIGINS debe incluir al menos un origen válido")
        return limpios

    @field_validator("S3_ENDPOINT_URL", "S3_BUCKET_NAME", "S3_REGION", "AWS_ACCESS_KEY_ID")
    @classmethod
    def limpiar_s3_strings(cls, v: str | None) -> str | None:
        if v is None:
            return None
        limpio = v.strip()
        if not limpio:
            return None
        if any(c.isspace() for c in limpio):
            raise ValueError("Variable S3 inválida: contiene espacios o comentarios en la misma línea")
        return limpio

    @field_validator("AWS_SECRET_ACCESS_KEY", mode="before")
    @classmethod
    def limpiar_secret_aws(cls, v):
        if v is None:
            return None
        if isinstance(v, SecretStr):
            limpio = v.get_secret_value().strip()
            return SecretStr(limpio) if limpio else None
        if isinstance(v, str):
            limpio = v.strip()
            return limpio if limpio else None
        return v

    @field_validator("MODELS_CACHE_DIR")
    @classmethod
    def limpiar_cache_dir(cls, v: str | None) -> str | None:
        if v is None:
            return None
        limpio = v.strip()
        return limpio or None

    @field_validator("S3_PREFIX")
    @classmethod
    def limpiar_s3_prefix(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validar_configuracion(self):
        # Validación de S3
        if self.STORAGE_BACKEND == "s3" and not self.S3_BUCKET_NAME:
            raise ValueError("STORAGE_BACKEND=s3 requiere S3_BUCKET_NAME")
        if bool(self.AWS_ACCESS_KEY_ID) != bool(self.AWS_SECRET_ACCESS_KEY):
            raise ValueError("Define AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY juntas (o ninguna, para usar un rol IAM)")

        # Validación de seguridad en producción
        if self.ENV == "prod":
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS no puede contener '*' en producción")
            if any(not o.startswith("https://") for o in self.CORS_ORIGINS):
                raise ValueError("Todos los CORS_ORIGINS deben usar https:// en producción")
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE debe ser True en producción")

        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SAMESITE='none' requiere COOKIE_SECURE=True")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()