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
from app.services.cuestionario import PREGUNTAS, SECTOR_KEY, RespuestasInvalidas, validar_respuestas
from app.services.explicabilidad import ModeloNoDisponible
from app.services.modelo_riesgo import predecir_riesgo
from app.services.recomendaciones import generar_recomendaciones

router = APIRouter(prefix="/v1/evaluacion", tags=["evaluacion"])

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