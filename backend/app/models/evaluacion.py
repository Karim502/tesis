"""Historial de evaluaciones de riesgo fiscal (usuarios registrados e invitados) + gestión de auditoría."""
import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, false, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EstadoAuditoria(str, enum.Enum):
    """Se guardan códigos estables; las etiquetas ("En Revisión", ...) viven en el frontend."""
    PENDIENTE = "PENDIENTE"
    EN_REVISION = "EN_REVISION"
    CERRADO = "CERRADO"


class Evaluacion(Base):
    __tablename__ = "evaluaciones"
    __table_args__ = (
        # Integridad de la muestra de tesis: un invitado NUNCA tiene dueño y un usuario SIEMPRE lo tiene.
        CheckConstraint(
            "(is_guest AND user_id IS NULL) OR (NOT is_guest AND user_id IS NOT NULL)",
            name="ck_evaluaciones_guest_consistente",
        ),
        CheckConstraint(
            "estado_auditoria IN ('PENDIENTE', 'EN_REVISION', 'CERRADO')",
            name="ck_evaluaciones_estado_auditoria",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # NULL => evaluación de invitado (modo diagnóstico rápido, sin cuenta).
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True, nullable=True
    )
    is_guest: Mapped[bool] = mapped_column(Boolean, server_default=false(), default=False, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    respuestas: Mapped[dict] = mapped_column(JSONB)
    nivel_riesgo: Mapped[str] = mapped_column(String(10))   # Bajo | Medio | Alto
    probabilidad: Mapped[float] = mapped_column(Float)      # 0..1 -> probabilidad de incumplimiento
    score: Mapped[int] = mapped_column(Integer)             # 0..100 -> puntaje de cumplimiento (mayor = mejor)
    recomendaciones: Mapped[list] = mapped_column(JSONB, default=list)  # [{id, titulo, detalle, prioridad, completada}]

    # Copia de respuestas["sector_economico"] en una columna propia: se filtra y se promedia por sector
    # con un índice normal, sin recorrer el JSON. La API la rellena al crear la evaluación.
    sector_economico: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    # --- Gestión de auditoría (solo el rol Auditor escribe aquí) ---
    estado_auditoria: Mapped[str] = mapped_column(
        String(15), server_default=EstadoAuditoria.PENDIENTE.value, default=EstadoAuditoria.PENDIENTE.value, index=True
    )
    notas_auditor: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Trazabilidad: quién y cuándo tocó el registro por última vez (útil para defender la tesis y para auditar al auditor).
    auditado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    auditado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
