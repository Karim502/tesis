"""CU01 - Evaluación de riesgo fiscal.

- Rutas de usuario: exigen rol Dueño de MYPE (RBAC).
- Rutas de invitado (`/cuestionario`, `/invitado`): públicas, sin JWT, pensadas para el
  trabajo de campo. Las evaluaciones de invitado se guardan con `is_guest = TRUE` y
  `user_id = NULL` para sumarlas a la muestra de investigación.
"""
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
from app.services.cuestionario import PREGUNTAS, SECTOR_KEY, RespuestasInvalidas, validar_respuestas
from app.services.modelo_riesgo import predecir_riesgo
from app.services.recomendaciones import generar_recomendaciones

router = APIRouter(prefix="/v1/evaluacion", tags=["evaluacion"])

# Guard RBAC reutilizado de CU04: un Auditor o Administrador recibe 403.
solo_mype = require_roles(Rol.DUENO_MYPE)

from collections import namedtuple

def _procesar(data: EvaluacionCreate) -> dict:
    """
    Pipeline ÚNICO para usuarios e invitados: valida -> predice -> genera recomendaciones.
    """
    try:
        respuestas_crudas = data.respuestas if hasattr(data, "respuestas") else data.model_dump()
        respuestas = validar_respuestas(respuestas_crudas or {})
    except RespuestasInvalidas as exc:
        raise HTTPException(
            422,
            detail={"code": "INVALID_ANSWERS", "message": "Revisa tus respuestas", "errores": getattr(exc, "errores", str(exc))},
        )

    # 1. Llamar al modelo predictivo
    pred_dict = predecir_riesgo(respuestas)

    # 2. Adaptar el diccionario para el generador de recomendaciones
    from collections import namedtuple
    PredObj = namedtuple("PredObj", ["nivel", "probabilidad", "score"])
    pred_obj = PredObj(
        nivel=pred_dict["nivel_riesgo"],
        probabilidad=pred_dict["probabilidad"],
        score=pred_dict["score"],
    )

    # 3. Guardar respuestas CRUDAS en BD para que SHAP y comparativo sectorial tengan los datos reales
    return {
        "respuestas": respuestas,
        "sector_economico": pred_dict.get("datos_procesados", {}).get("sector_economico", "Bazar_VentaVar"),
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
@limiter.limit(lambda: settings.GUEST_RATE_LIMIT)  # freno anti-bots / anti-contaminación de la muestra
def crear_evaluacion_invitado(request: Request, data: EvaluacionCreate, db: Session = Depends(get_db)):
    """
    Diagnóstico rápido SIN cuenta. No depende de get_current_user y no emite ningún token.
    Se guarda con is_guest=True y user_id=NULL. No se almacena IP, nombre ni correo.
    """
    evaluacion = Evaluacion(is_guest=True, user_id=None, **_procesar(data))
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)
    return evaluacion  # el esquema de salida omite id y respuestas


# --------------------------------------------------------------------- Dueño de MYPE

@router.post("", response_model=EvaluacionOut, status_code=status.HTTP_201_CREATED)
def crear_evaluacion(data: EvaluacionCreate, db: Session = Depends(get_db), user: Usuario = Depends(solo_mype)):
    evaluacion = Evaluacion(
        user_id=user.id,  # SEGURIDAD: el dueño sale del token, jamás del cuerpo de la petición
        is_guest=False,
        **_procesar(data),
    )
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)  # trae id y creado_en generados por la BD
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
    if ev is None or rec_id not in {r["id"] for r in ev.recomendaciones}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "No encontrado"})

    # Se reasigna una lista nueva: SQLAlchemy no detecta mutaciones internas de JSONB.
    ev.recomendaciones = [
        {**r, "completada": data.completada} if r["id"] == rec_id else r for r in ev.recomendaciones
    ]
    db.commit()
    return ev
