"""Esquemas del módulo de auditoría (rol Auditor)."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.evaluacion import EstadoAuditoria

NOTAS_MAX = 2000


def _limpiar_nota(v: str | None) -> str | None:
    # Texto vacío o solo espacios => sin nota (NULL). No se altera el contenido: React lo escapa al mostrarlo.
    v = v.strip() if v else v
    return v or None


class AuditoriaUpdate(BaseModel):
    """
    Cuerpo del PUT: reemplaza estado y notas (semántica PUT). `estado_auditoria` solo acepta los tres
    códigos del enum: cualquier otro valor => 422 automático.
    """
    estado_auditoria: EstadoAuditoria
    notas_auditor: Annotated[str | None, Field(max_length=NOTAS_MAX)] = None

    @field_validator("notas_auditor")
    @classmethod
    def limpiar(cls, v: str | None) -> str | None:
        return _limpiar_nota(v)


class AuditoriaPatch(BaseModel):
    """
    Cuerpo del PATCH: actualización PARCIAL. Solo se tocan los campos que llegan en el JSON:
      {"estado_auditoria": "CERRADO"}                 -> cambia el estado y deja la nota como está
      {"notas_auditor": "texto"}                      -> cambia la nota y deja el estado
      {"notas_auditor": null}  (o "")                 -> borra la nota
    Así dos auditores que editan campos distintos no se pisan entre sí.
    """
    estado_auditoria: EstadoAuditoria | None = None
    notas_auditor: Annotated[str | None, Field(max_length=NOTAS_MAX)] = None

    @field_validator("notas_auditor")
    @classmethod
    def limpiar(cls, v: str | None) -> str | None:
        return _limpiar_nota(v)

    @model_validator(mode="after")
    def validar_campos(self):
        enviados = self.model_fields_set & {"estado_auditoria", "notas_auditor"}
        if not enviados:
            raise ValueError("Envía al menos estado_auditoria o notas_auditor")
        if "estado_auditoria" in enviados and self.estado_auditoria is None:
            raise ValueError("estado_auditoria no puede ser null")
        return self


class EvaluacionAuditorOut(BaseModel):
    id: int
    creado_en: datetime
    mype_nombre: str
    mype_email: str
    sector_economico: str | None
    nivel_riesgo: Literal["Bajo", "Medio", "Alto"]
    probabilidad: float
    score: int
    respuestas: dict
    estado_auditoria: EstadoAuditoria
    notas_auditor: str | None
    auditado_en: datetime | None
    auditado_por_nombre: str | None


class PadronOut(BaseModel):
    items: list[EvaluacionAuditorOut]
    total: int      # total que cumple los filtros (para "Mostrando X de Y")
    limit: int
    offset: int
