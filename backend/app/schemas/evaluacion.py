from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ValorRespuesta = Annotated[str, Field(max_length=200)]


class EvaluacionCreate(BaseModel):
    # Tope de claves y longitud por valor: protege el endpoint público de invitado.
    # El contenido exacto contra el catálogo se valida en services/cuestionario.py.
    respuestas: Annotated[dict[str, ValorRespuesta], Field(max_length=64)]


class RecomendacionOut(BaseModel):
    id: str
    titulo: str
    detalle: str
    prioridad: Literal["alta", "media", "baja"]
    completada: bool


class EvaluacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    creado_en: datetime
    nivel_riesgo: Literal["Bajo", "Medio", "Alto"]
    probabilidad: float
    score: int
    respuestas: dict[str, str]
    recomendaciones: list[RecomendacionOut]

    @field_validator("respuestas", mode="before")
    @classmethod
    def _normalizar_respuestas_nulas(cls, v):
        return {} if v is None else v


class TareaUpdate(BaseModel):
    completada: bool


class EvaluacionInvitadoOut(BaseModel):
    """
    Respuesta al invitado. Deliberadamente SIN `id` ni `respuestas`: el invitado no tiene historial
    ni puede volver a consultar el registro, y así no se expone el contador de la muestra.
    """
    model_config = ConfigDict(from_attributes=True)

    creado_en: datetime
    nivel_riesgo: Literal["Bajo", "Medio", "Alto"]
    probabilidad: float
    score: int
    recomendaciones: list[RecomendacionOut]