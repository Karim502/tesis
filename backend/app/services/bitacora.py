"""Registro en la bitácora de auditoría (tabla audit_logs)."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import Usuario

log = logging.getLogger(__name__)


def _ip(request: Request | None) -> str | None:
    # Detrás del proxy de Render, request.client es el proxy: arranca uvicorn con --proxy-headers
    # (y --forwarded-allow-ips) para que aquí llegue la IP real del cliente.
    return request.client.host[:45] if request is not None and request.client else None


def registrar(
    db: Session,
    usuario: Usuario | None,
    accion: str,
    *,
    recurso_tipo: str | None = None,
    recurso_id: int | None = None,
    detalle: dict | None = None,
    request: Request | None = None,
    commit: bool = True,
) -> None:
    """
    Agrega un evento a la bitácora.
      · commit=True  (lecturas y login): se confirma aparte y un fallo de la bitácora NUNCA rompe la operación principal.
      · commit=False (acciones del admin): el evento se une a la transacción del llamador; si la acción falla, no queda registro,
        y si se confirma, quedan ambos o ninguno.
    NO guardar contraseñas, tokens ni el texto de las notas en `detalle`.
    """
    evento = AuditLog(
        usuario_id=usuario.id if usuario else None,
        usuario_email=usuario.email if usuario else None,
        usuario_rol=usuario.rol.value if usuario else None,
        accion=accion,
        recurso_tipo=recurso_tipo,
        recurso_id=recurso_id,
        detalle=detalle,
        ip=_ip(request),
    )
    if not commit:
        db.add(evento)
        return
    try:
        db.add(evento)
        db.commit()
    except Exception:  # la bitácora es importante, pero no debe tumbar una consulta del auditor
        db.rollback()
        log.exception("No se pudo registrar el evento de bitácora %s", accion)


def ya_registrado_reciente(db: Session, usuario: Usuario, accion: str, recurso_id: int, minutos: int = 5) -> bool:
    """Evita llenar la bitácora cuando el mismo auditor reabre la misma evaluación varias veces seguidas."""
    desde = datetime.now(timezone.utc) - timedelta(minutes=minutos)
    return db.execute(
        select(AuditLog.id).where(
            AuditLog.usuario_id == usuario.id, AuditLog.accion == accion,
            AuditLog.recurso_id == recurso_id, AuditLog.creado_en >= desde,
        ).limit(1)
    ).first() is not None
