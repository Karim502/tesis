from collections import namedtuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.evaluacion import Evaluacion
from app.models.user import Rol, Usuario
from app.schemas.evaluacion import EvaluacionCreate, EvaluacionInvitadoOut, EvaluacionOut, TareaUpdate
from app.services.cuestionario import PREGUNTAS, RespuestasInvalidas, validar_respuestas
from app.services.explicabilidad import ModeloNoDisponible
from app.services.modelo_riesgo import predecir_riesgo
from app.services.recomendaciones import generar_recomendaciones

router = APIRouter(prefix="/evaluacion", tags=["evaluacion"])

# Guard RBAC reutilizado de CU04: un Auditor o Administrador recibe 403.
solo_mype = require_roles(Rol.DUENO_MYPE)

PredObj = namedtuple("PredObj", ["nivel", "probabilidad", "score"])


def _procesar(data: EvaluacionCreate) -> dict:
    """
    Pipeline ÚNICO para usuarios e invitados: valida -> predice -> genera recomendaciones.
    """
    try:
        respuestas = validar_respuestas(data.respuestas)
    except RespuestasInvalidas as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_ANSWERS",
                "message": "Revisa tus respuestas",
                "errores": exc.errores,
            },
        )

    try:
        pred_dict = predecir_riesgo(respuestas)
    except ModeloNoDisponible:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_NOT_AVAILABLE",
                "message": "El servicio de evaluación no está disponible temporalmente. Intenta nuevamente en unos minutos.",
            },
        )

    pred_obj = PredObj(
        nivel=pred_dict["nivel_riesgo"],
        probabilidad=pred_dict["probabilidad"],
        score=pred_dict["score"],
    )

    return {
        "respuestas": respuestas,
        "sector_economico": pred_dict["datos_procesados"]["sector_economico"],
        "nivel_riesgo": pred_dict["nivel_riesgo"],
        "probabilidad": pred_dict["probabilidad"],
        "score": pred_dict["score"],
        "recomendaciones": generar_recomendaciones(respuestas, pred_obj),
    }


# --------------------------------------------------------------------------- público


@router.get("/cuestionario")
def obtener_cuestionario():
    """Catálogo de preguntas. Público: el invitado lo necesita y no contiene datos sensibles."""
    return {"preguntas": PREGUNTAS}


@router.post("/invitado", response_model=EvaluacionInvitadoOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: settings.GUEST_RATE_LIMIT)
def crear_evaluacion_invitado(request: Request, data: EvaluacionCreate, db: Session = Depends(get_db)):
    """
    Diagnóstico rápido SIN cuenta. No depende de get_current_user y no emite ningún token.
    Se guarda con is_guest=True y user_id=NULL. No se almacena IP, nombre ni correo.
    """
    evaluacion = Evaluacion(is_guest=True, user_id=None, **_procesar(data))
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)
    return evaluacion


# --------------------------------------------------------------------- Dueño de MYPE


@router.post("", response_model=EvaluacionOut, status_code=status.HTTP_201_CREATED)
def crear_evaluacion(data: EvaluacionCreate, db: Session = Depends(get_db), user: Usuario = Depends(solo_mype)):
    evaluacion = Evaluacion(
        user_id=user.id,
        is_guest=False,
        **_procesar(data),
    )
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)
    return evaluacion


@router.get("/historial", response_model=list[EvaluacionOut])
def historial(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(solo_mype),
):
    """Solo las evaluaciones del usuario autenticado (nunca las de invitados), de la más reciente a la más antigua."""
    stmt = (
        select(Evaluacion)
        .where(Evaluacion.user_id == user.id)
        .order_by(Evaluacion.creado_en.desc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


@router.patch("/{evaluacion_id}/recomendaciones/{rec_id}", response_model=EvaluacionOut)
def marcar_recomendacion(
    evaluacion_id: int,
    rec_id: str,
    data: TareaUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(solo_mype),
):
    """Guarda el avance del checklist. Filtra por user_id para impedir acceder a evaluaciones ajenas (IDOR)."""
    ev = db.execute(
        select(Evaluacion).where(Evaluacion.id == evaluacion_id, Evaluacion.user_id == user.id)
    ).scalar_one_or_none()
    recs = (ev.recomendaciones or []) if ev is not None else []
    if ev is None or rec_id not in {r.get("id") for r in recs if isinstance(r, dict)}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "No encontrado"})

    ev.recomendaciones = [
        {**r, "completada": data.completada} if isinstance(r, dict) and r.get("id") == rec_id else r
        for r in recs
    ]
    db.commit()
    db.refresh(ev)
    return ev