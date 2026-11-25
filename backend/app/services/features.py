"""
PUNTO DE INTEGRACIÓN CON TU MODELO ENTRENADO.

`construir_features` convierte las respuestas guardadas de una evaluación en la fila que espera el modelo.
Debe reproducir EXACTAMENTE el preprocesamiento del entrenamiento. La versión por defecto cubre los dos casos
más comunes; si tu entrenamiento hizo otra cosa (codificación ordinal manual, ratios derivados, escalado...),
adapta SOLO esta función y el resto del endpoint SHAP no cambia:

  - Estimador de árboles entrenado con un DataFrame de pandas (columnas de texto como `category`):
      las respuestas de texto se pasan como `category`; LightGBM/XGBoost reasignan las categorías con las que
      se entrenó. Es el caso por defecto (`como_categoria=True`).
  - sklearn Pipeline (ColumnTransformer + árbol): se pasan los textos tal cual (`como_categoria=False`)
      y el propio Pipeline hace la codificación.
"""


class FeaturesFaltantes(Exception):
    """La evaluación no tiene respuestas para alguna columna que el modelo necesita."""

    def __init__(self, faltantes: list[str]):
        super().__init__(", ".join(faltantes))
        self.faltantes = faltantes


def construir_features(respuestas: dict, columnas: list[str], como_categoria: bool = True):
    import pandas as pd

    if not respuestas:
        raise FeaturesFaltantes(columnas)

    # Retrocompatibilidad: si el registro en BD ya tiene las 16 variables procesadas (evaluaciones antiguas)
    if all(c in respuestas for c in columnas):
        respuestas_modelo = dict(respuestas)
    else:
        # Usamos la misma transformación exacta de modelo_riesgo.py para garantizar 100% de coherencia
        from app.services.modelo_riesgo import predecir_riesgo
        pred = predecir_riesgo(respuestas)
        respuestas_modelo = pred["datos_procesados"]

    faltantes = [c for c in columnas if respuestas_modelo.get(c) is None]
    if faltantes:
        raise FeaturesFaltantes(faltantes)

    df = pd.DataFrame([{c: respuestas_modelo[c] for c in columnas}], columns=columnas)

    if como_categoria:
        for c in columnas:
            if not pd.api.types.is_numeric_dtype(df[c]):
                df[c] = df[c].astype("category")
    return df