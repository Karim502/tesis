"""Esquemas del análisis por evaluación: comparativo sectorial y explicabilidad SHAP."""
from typing import Literal

from pydantic import BaseModel


class ComparativoSectorialOut(BaseModel):
    """Todas las probabilidades son fracciones 0-1 (igual que el resto de la API)."""
    evaluacion_id: int
    sector: str | None
    sector_etiqueta: str | None
    probabilidad: float                  # de la MYPE seleccionada
    promedio_sector: float | None        # None si la MYPE no tiene sector registrado
    n_sector: int                        # evaluaciones que entran en ese promedio
    promedio_general: float | None
    n_general: int
    diferencia_sector: float | None      # probabilidad - promedio_sector (en fracción; +0.18 = 18 puntos sobre el sector)
    muestra_suficiente: bool
    minimo_muestra: int


class ShapContribucion(BaseModel):
    variable: str
    etiqueta: str
    valor: int | float | str | None
    shap: float                          # contribución a la predicción, en el espacio nativo del modelo (ver `espacio`)


class ShapOtras(BaseModel):
    cantidad: int
    shap: float


class ShapOut(BaseModel):
    evaluacion_id: int
    modelo: str
    clase_riesgo: str
    espacio: Literal["log-odds", "probabilidad", "desconocido"]
    valor_base: float                    # E[f(X)]: lo que predice el modelo "en promedio"
    prediccion: float                    # f(x) = valor_base + suma de TODAS las contribuciones
    probabilidad_base: float | None      # valor_base expresado como probabilidad (0-1)
    probabilidad: float | None           # predict_proba del modelo para esta MYPE (0-1)
    contribuciones: list[ShapContribucion]
    otras: ShapOtras | None
