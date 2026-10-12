"""Historial de evaluaciones de riesgo fiscal (usuarios registrados e invitados)."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, false, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Evaluacion(Base):
    __tablename__ = "evaluaciones"
    __table_args__ = (
        # Integridad de la muestra de tesis: un invitado NUNCA tiene dueño y un usuario SIEMPRE lo tiene.
        # Lo impone la base de datos, por lo que ningún bug de la API puede dejar registros ambiguos.
        CheckConstraint(
            "(is_guest AND user_id IS NULL) OR (NOT is_guest AND user_id IS NOT NULL)",
            name="ck_evaluaciones_guest_consistente",
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
