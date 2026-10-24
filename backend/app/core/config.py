"""Configuración centralizada. Los secretos vienen del entorno (.env), nunca del código."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = True
    # Límite del endpoint público de invitados, por IP. Ajustar según el evento (ver README).
    GUEST_RATE_LIMIT: str = "30/hour"

    # --- Explicabilidad (SHAP) y comparativo sectorial ---
    # Ruta del modelo entrenado: relativa a /backend o absoluta. Es un archivo de CONFIANZA que despliegas tú.
    MODELO_PATH: str = "models/modelo_ganador.joblib"
    # Etiqueta (tal como aparece en model.classes_) de la clase que significa "riesgo". En binario suele ser 1.
    MODELO_CLASE_RIESGO: str = "1"
    # Con menos evaluaciones que esto en el sector, el promedio se marca como "muestra insuficiente".
    SECTOR_MUESTRA_MINIMA: int = 5
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # SEGURIDAD: el algoritmo es fijo en código (no viene del token ni de la petición).
    # Evita ataques de "algorithm confusion" (p. ej. alg=none) al decodificar.
    JWT_ALGORITHM: str = "HS256"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY debe tener al menos 32 caracteres")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
