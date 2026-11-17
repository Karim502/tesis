"""Análisis por evaluación para el Auditor: comparativo sectorial y explicabilidad SHAP. Solo rol AUDITOR."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.auditoria import evaluacion_auditable, solo_auditor
from app.core.config import settings
from app.db.session import get_db
from app.models.evaluacion import Evaluacion
from app.models.user import Usuario
from app.schemas.analisis import ComparativoSectorialOut, ShapOut
from app.services.cuestionario import etiqueta_sector
from app.services.explicabilidad import ModeloNoDisponible, explicar
from app.services.features import FeaturesFaltantes

log = logging.getLogger(__name__)
router = APIRouter(prefix="/evaluaciones", tags=["analisis"])

_MENSAJE_MODELO = {
    "archivo_ausente": "El modelo de explicabilidad no está instalado en el servidor.",
    "dependencias": "Faltan las librerías de explicabilidad en el servidor.",
    "carga": "El modelo de explicabilidad no se pudo cargar.",
    "configuracion": "La configuración del modelo de explicabilidad no es válida.",
}


@router.get("/{evaluacion_id}/comparativo-sectorial", response_model=ComparativoSectorialOut)
def comparativo_sectorial(
    evaluacion_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(solo_auditor),
):
    ev = evaluacion_auditable(db, evaluacion_id)

    # 1. Intentar obtener el sector de la columna de la DB o del JSON de respuestas
    respuestas = ev.respuestas or {}
    sector_registrado = ev.sector_economico or respuestas.get("var_2_subsector_comercial")

    prom_general, n_general = db.execute(select(func.avg(Evaluacion.probabilidad), func.count())).one()
    prom_sector, n_sector = None, 0

    if sector_registrado:
        # Consulta los promedios agrupando por el sector encontrado
        prom_sector, n_sector = db.execute(
            select(func.avg(Evaluacion.probabilidad), func.count()).where(
                (Evaluacion.sector_economico == sector_registrado) | 
                (Evaluacion.respuestas["var_2_subsector_comercial"].astext == sector_registrado)
            )
        ).one()

    prom_sector = float(prom_sector) if prom_sector is not None else None

    return ComparativoSectorialOut(
        evaluacion_id=ev.id,
        sector=sector_registrado,
        sector_etiqueta=etiqueta_sector(sector_registrado),
        probabilidad=ev.probabilidad,
        promedio_sector=prom_sector,
        n_sector=n_sector,
        promedio_general=float(prom_general) if prom_general is not None else None,
        n_general=n_general,
        diferencia_sector=(ev.probabilidad - prom_sector) if prom_sector is not None else None,
        muestra_suficiente=n_sector >= settings.SECTOR_MUESTRA_MINIMA,
        minimo_muestra=settings.SECTOR_MUESTRA_MINIMA,
    )


import json

@router.get("/{evaluacion_id}/shap", response_model=ShapOut)
def explicabilidad_shap(
    evaluacion_id: int,
    max_display: int = Query(12, ge=1, le=50, description="Variables a mostrar; el resto se agrupa en 'otras'"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(solo_auditor),
):
    """
    Valores SHAP locales de UNA evaluación (variable, valor de la variable, contribución) en JSON.
    Endpoint síncrono a propósito: FastAPI lo ejecuta en un hilo y no bloquea al resto de peticiones.
    """
    ev = evaluacion_auditable(db, evaluacion_id)
    try:
        # 1. Asegurar que respuestas sea un diccionario utilizable
        resp = ev.respuestas or {}
        if isinstance(resp, str):
            resp = json.loads(resp)
            
        # 2. Inyectar variables que viven en sus propias columnas en la base de datos
        respuestas_completas = {**resp}
        if ev.sector_economico and "sector_economico" not in respuestas_completas:
            respuestas_completas["sector_economico"] = ev.sector_economico

        datos = explicar(respuestas_completas, max_display)
        
    except ModeloNoDisponible as exc:
        raise HTTPException(503, detail={"code": "MODEL_NOT_AVAILABLE", "message": _MENSAJE_MODELO[exc.motivo]})
    except FeaturesFaltantes as exc:
        raise HTTPException(
            422,
            detail={
                "code": "FEATURES_MISSING",
                "message": "Esta evaluación no tiene todas las respuestas que requiere el modelo.",
                "faltantes": exc.faltantes,
            },
        )
    except Exception:
        log.exception("Falló el cálculo SHAP de la evaluación %s", evaluacion_id)  
        raise HTTPException(500, detail={"code": "EXPLANATION_FAILED", "message": "No se pudo calcular la explicación."})
        
    return ShapOut(evaluacion_id=ev.id, **datos)
