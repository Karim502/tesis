from datetime import datetime
from typing import Literal

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class EvaluacionCreate(BaseModel):
    # Tope de claves: el endpoint de invitado es público y no debe aceptar cuerpos gigantes.
    # El contenido se valida después contra el catálogo (services/cuestionario.py).
    respuestas: Annotated[dict[str, str | int | float], Field(max_length=64)]


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
    respuestas: dict
    recomendaciones: list[RecomendacionOut]


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
