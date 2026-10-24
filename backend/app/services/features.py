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
    """DataFrame de UNA fila con las columnas en el orden que espera el modelo."""
    import pandas as pd  # import perezoso: la API arranca aunque pandas no esté instalado

    # Estricto a propósito: rellenar en silencio una variable ausente daría una explicación engañosa.
    faltantes = [c for c in columnas if respuestas.get(c) is None]
    if faltantes:
        raise FeaturesFaltantes(faltantes)

    df = pd.DataFrame([{c: respuestas[c] for c in columnas}], columns=columnas)
    if como_categoria:
        for c in columnas:
            if not pd.api.types.is_numeric_dtype(df[c]):
                df[c] = df[c].astype("category")
    return df
