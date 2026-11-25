"""Configuración centralizada. Los secretos vienen del entorno (.env), nunca del código."""
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    GUEST_RATE_LIMIT: str = "30/hour"

    # --- Modelos, Explicabilidad y Reentrenamiento (MLOps) ---
    MODELS_DIR: str = "models"
    MODELO_PATH: str = "ml_models/modelo_ganador.joblib"
    MODELO_CLASE_RIESGO: str = "1"
    SECTOR_MUESTRA_MINIMA: int = 5

    ENTRENAMIENTO_CSV_PATH: str = "data/dataset_entrenamiento.csv"
    ENTRENAMIENTO_TARGET: str = "riesgo"
    ENTRENAMIENTO_FEATURES: list[str] | None = None
    ENTRENAMIENTO_MAX_MB: int = 5
    ENTRENAMIENTO_MIN_FILAS: int = 60
    ENTRENAMIENTO_TIMEOUT_MIN: int = 60

    # --- Almacenamiento S3 (MLOps) ---
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    S3_BUCKET_NAME: str | None = None
    S3_PREFIX: str = "models/"
    S3_REGION: str | None = None
    S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: SecretStr | None = None
    MODELS_CACHE_DIR: str | None = None

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY debe tener al menos 32 caracteres")
        return v

    @model_validator(mode="after")
    def validar_configuracion(self):
        # Validación de S3
        if self.STORAGE_BACKEND == "s3" and not self.S3_BUCKET_NAME:
            raise ValueError("STORAGE_BACKEND=s3 requiere S3_BUCKET_NAME")
        if bool(self.AWS_ACCESS_KEY_ID) != bool(self.AWS_SECRET_ACCESS_KEY):
            raise ValueError("Define AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY juntas (o ninguna, para usar un rol IAM)")

        # Validación de seguridad en producción
        if self.ENV == "prod" and "*" in self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS no puede contener '*' en producción")
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SAMESITE='none' requiere COOKIE_SECURE=True")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()