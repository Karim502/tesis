"""Módulo del Auditor: padrón de evaluaciones con filtros avanzados y gestión de estado/notas. Solo rol AUDITOR."""
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.evaluacion import EstadoAuditoria, Evaluacion
from app.models.user import Rol, Usuario
from app.schemas.auditoria import AuditoriaPatch, AuditoriaUpdate, EvaluacionAuditorOut, PadronOut
from app.services.bitacora import registrar

router = APIRouter(prefix="/evaluaciones", tags=["auditoria"])

# RBAC: Dueño de MYPE y Administrador reciben 403. Se valida en el servidor en cada petición.
solo_auditor = require_roles(Rol.AUDITOR)

# Las fechas del filtro son fechas CALENDARIO de Perú (UTC-5, sin horario de verano), no de UTC.
LIMA = timezone(timedelta(hours=-5))
FECHA_MIN, FECHA_MAX = date(2000, 1, 1), date(2100, 12, 31)


def _limites_utc(fecha_inicio: date | None, fecha_fin: date | None):
    """
    Rango [desde, hasta) en UTC. `fecha_fin` es INCLUSIVA: se usa el inicio del día siguiente como
    límite exclusivo, así una evaluación de las 23:59 del último día sí entra.
    """
    desde = hasta = None
    if fecha_inicio:
        desde = datetime.combine(fecha_inicio, time.min, tzinfo=LIMA).astimezone(timezone.utc)
    if fecha_fin:
        hasta = datetime.combine(fecha_fin + timedelta(days=1), time.min, tzinfo=LIMA).astimezone(timezone.utc)
    return desde, hasta


def _error_rango(code: str, message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": code, "message": message})


def evaluacion_auditable(db: Session, evaluacion_id: int) -> Evaluacion:
    """
    Evaluación sobre la que el auditor puede trabajar (la de una MYPE con cuenta) o 404.
    Las de invitados son anónimas y quedan fuera. Lo comparten el padrón, el PATCH/PUT, el SHAP y el comparativo.
    """
    ev = db.execute(
        select(Evaluacion).where(Evaluacion.id == evaluacion_id)
    ).scalar_one_or_none()
    if ev is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "Evaluación no encontrada"})
    return ev


def _salida(ev: Evaluacion, mype: Usuario | None, auditor: Usuario | None) -> EvaluacionAuditorOut:
    return EvaluacionAuditorOut(
        id=ev.id,
        creado_en=ev.creado_en,
        mype_nombre=mype.nombre if mype else "Invitado Anónimo",
        mype_email=mype.email if mype else "Sin correo",
        sector_economico=ev.sector_economico,
        nivel_riesgo=ev.nivel_riesgo,
        probabilidad=ev.probabilidad,
        score=ev.score,
        respuestas=ev.respuestas,
        estado_auditoria=ev.estado_auditoria,
        notas_auditor=ev.notas_auditor,
        auditado_en=ev.auditado_en,
        auditado_por_nombre=auditor.nombre if auditor else None,
    )


def _salida_actual(db: Session, ev: Evaluacion) -> EvaluacionAuditorOut:
    revisor = db.get(Usuario, ev.auditado_por) if ev.auditado_por else None
    return _salida(ev, db.get(Usuario, ev.user_id), revisor)


@router.get("", response_model=PadronOut)
def listar_padron(
    estado_auditoria: EstadoAuditoria | None = Query(None, description="PENDIENTE | EN_REVISION | CERRADO"),
    sector_economico: str | None = Query(None, min_length=1, max_length=40, pattern=r"^[a-z0-9_]+$"),
    probabilidad_min: float | None = Query(None, ge=0, le=100, description="Riesgo mínimo en %, inclusive (ej. 80)"),
    probabilidad_max: float | None = Query(None, ge=0, le=100, description="Riesgo máximo en %, inclusive"),
    fecha_inicio: date | None = Query(None, ge=FECHA_MIN, le=FECHA_MAX, description="Inclusive (YYYY-MM-DD, hora de Perú)"),
    fecha_fin: date | None = Query(None, ge=FECHA_MIN, le=FECHA_MAX, description="Inclusive (YYYY-MM-DD, hora de Perú)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Usuario = Depends(solo_auditor),
):
    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise _error_rango("INVALID_RANGE", "La fecha de inicio no puede ser posterior a la fecha fin")
    if probabilidad_min is not None and probabilidad_max is not None and probabilidad_min > probabilidad_max:
        raise _error_rango("INVALID_RISK_RANGE", "El riesgo mínimo no puede ser mayor que el máximo")

    # Filtros opcionales: solo se agregan los que llegaron. Todos son parámetros enlazados (sin SQL concatenado).
    filtros = []
    if estado_auditoria:
        filtros.append(Evaluacion.estado_auditoria == estado_auditoria.value)
    if sector_economico:
        filtros.append(Evaluacion.sector_economico == sector_economico)
    # La API habla en porcentaje (0-100); la columna guarda la probabilidad como fracción (0-1).
    if probabilidad_min is not None:
        filtros.append(Evaluacion.probabilidad >= probabilidad_min / 100)
    if probabilidad_max is not None:
        filtros.append(Evaluacion.probabilidad <= probabilidad_max / 100)
    desde, hasta = _limites_utc(fecha_inicio, fecha_fin)
    if desde:
        filtros.append(Evaluacion.creado_en >= desde)
    if hasta:
        filtros.append(Evaluacion.creado_en < hasta)

    total = db.execute(select(func.count()).select_from(Evaluacion).where(*filtros)).scalar_one()

    auditor = aliased(Usuario)
    filas = db.execute(
        select(Evaluacion, Usuario, auditor)
        .outerjoin(Usuario, Usuario.id == Evaluacion.user_id)  # <-- SE CAMBIÓ A outerjoin
        .outerjoin(auditor, auditor.id == Evaluacion.auditado_por)
        .where(*filtros)
        .order_by(Evaluacion.creado_en.desc(), Evaluacion.id.desc())  # id desempata: paginación estable
        .limit(limit)
        .offset(offset)
    ).all()

    return PadronOut(items=[_salida(e, m, a) for e, m, a in filas], total=total, limit=limit, offset=offset)


@router.patch("/{evaluacion_id}/auditoria", response_model=EvaluacionAuditorOut)
def parchear_auditoria(
    evaluacion_id: int,
    data: AuditoriaPatch,
    request: Request,
    db: Session = Depends(get_db),
    auditor: Usuario = Depends(solo_auditor),
):
    """
    Actualización PARCIAL del estado y/o de la nota interna (solo cambia lo que llega en el cuerpo).
    Si nada cambia realmente, no se toca la trazabilidad (quién/cuándo). Devuelve el registro actual.
    """
    ev = evaluacion_auditable(db, evaluacion_id)
    estado_antes = ev.estado_auditoria
    cambio = False
    notas_modificadas = False

    if "estado_auditoria" in data.model_fields_set and data.estado_auditoria.value != ev.estado_auditoria:
        ev.estado_auditoria = data.estado_auditoria.value
        cambio = True
    if "notas_auditor" in data.model_fields_set and data.notas_auditor != ev.notas_auditor:
        ev.notas_auditor = data.notas_auditor
        cambio = True
        notas_modificadas = True

    if cambio:
        ev.auditado_por = auditor.id  # SEGURIDAD: el auditor sale del token, jamás del cuerpo de la petición
        ev.auditado_en = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ev)

        detalle = {}
        if ev.estado_auditoria != estado_antes:
            detalle["estado"] = {"antes": estado_antes, "despues": ev.estado_auditoria}
        if notas_modificadas:
            detalle["notas_modificadas"] = True
        registrar(
            db,
            auditor,
            "AUDITORIA_ACTUALIZADA",
            recurso_tipo="evaluacion",
            recurso_id=ev.id,
            detalle=detalle,
            request=request,
        )
    return _salida_actual(db, ev)

@router.put("/{evaluacion_id}/auditoria", response_model=EvaluacionAuditorOut)
def actualizar_auditoria(
    evaluacion_id: int,
    data: AuditoriaUpdate,
    db: Session = Depends(get_db),
    auditor: Usuario = Depends(solo_auditor),
):
    """Reemplazo COMPLETO de estado y nota (semántica PUT). El panel usa PATCH; este se mantiene por compatibilidad."""
    ev = evaluacion_auditable(db, evaluacion_id)
    ev.estado_auditoria = data.estado_auditoria.value
    ev.notas_auditor = data.notas_auditor
    ev.auditado_por = auditor.id
    ev.auditado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ev)
    return _salida(ev, db.get(Usuario, ev.user_id), auditor)
