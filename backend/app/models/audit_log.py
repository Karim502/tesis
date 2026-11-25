"""Bitácora de auditoría: quién hizo qué, sobre qué recurso y cuándo. Solo se INSERTA; nunca se edita."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Accion:
    """Catálogo de acciones registradas (texto estable: se guarda tal cual en la BD)."""
    LOGIN = "LOGIN"
    EVALUACION_CONSULTADA = "EVALUACION_CONSULTADA"      # el auditor abrió/revisó una evaluación
    AUDITORIA_ACTUALIZADA = "AUDITORIA_ACTUALIZADA"      # cambió estado y/o notas
    AUDITOR_CREADO = "AUDITOR_CREADO"
    AUDITOR_ACTUALIZADO = "AUDITOR_ACTUALIZADO"
    AUDITOR_SUSPENDIDO = "AUDITOR_SUSPENDIDO"
    AUDITOR_REACTIVADO = "AUDITOR_REACTIVADO"
    AUDITOR_ELIMINADO = "AUDITOR_ELIMINADO"
    MODELO_REENTRENAMIENTO = "MODELO_REENTRENAMIENTO"
    MODELO_ACTIVADO = "MODELO_ACTIVADO"

    TODAS = (
        LOGIN, EVALUACION_CONSULTADA, AUDITORIA_ACTUALIZADA, AUDITOR_CREADO, AUDITOR_ACTUALIZADO,
        AUDITOR_SUSPENDIDO, AUDITOR_REACTIVADO, AUDITOR_ELIMINADO, MODELO_REENTRENAMIENTO, MODELO_ACTIVADO,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_fecha", "creado_en"),
        Index("idx_audit_logs_usuario_fecha", "usuario_id", "creado_en"),
        Index("idx_audit_logs_accion_fecha", "accion", "creado_en"),
        Index("idx_audit_logs_recurso", "recurso_tipo", "recurso_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # El usuario puede ser eliminado después: la FK pasa a NULL, pero el correo/rol quedan "congelados" aquí,
    # así la bitácora sigue diciendo quién hizo cada cosa aunque la cuenta ya no exista.
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario_email: Mapped[str | None] = mapped_column(String(255))
    usuario_rol: Mapped[str | None] = mapped_column(String(20))

    accion: Mapped[str] = mapped_column(String(40))
    recurso_tipo: Mapped[str | None] = mapped_column(String(30))   # evaluacion | usuario | modelo
    recurso_id: Mapped[int | None] = mapped_column(BigInteger)
    detalle: Mapped[dict | None] = mapped_column(JSONB)            # contexto no sensible (nunca contraseñas ni notas)
    ip: Mapped[str | None] = mapped_column(String(45))             # IPv4/IPv6
