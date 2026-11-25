"""
Explicabilidad LOCAL con SHAP (TreeExplainer) para una evaluación concreta.

Devuelve estructuras JSON listas para graficar en el navegador: aquí NO se generan imágenes (nada de matplotlib).
Las librerías pesadas (shap, joblib, numpy) se importan de forma perezosa: la API arranca aunque falten, y el
endpoint responde 503 con un mensaje claro en lugar de impedir que todo el servidor levante.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.cuestionario import PREGUNTAS, etiqueta_sector

log = logging.getLogger(__name__)

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
_PREGUNTAS = {p["id"]: p for p in PREGUNTAS}


class ModeloNoDisponible(Exception):
    """No hay modelo utilizable: falta el archivo, faltan librerías o el archivo no es compatible."""

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo  # archivo_ausente | dependencias | carga | configuracion


@dataclass(frozen=True)
class ModeloCargado:
    estimador: Any                  # el modelo de árboles (último paso si el objeto es un Pipeline)
    preprocesador: Any | None       # pasos previos del Pipeline, o None
    explainer: Any                  # shap.TreeExplainer ya construido (es lo más caro: se crea una vez)
    columnas: tuple[str, ...]       # columnas de ENTRADA (las que se arman desde las respuestas)
    nombres_modelo: tuple[str, ...]  # columnas que ve el árbol (tras el preprocesador)
    idx_clase: int | None           # posición de la clase "riesgo" en classes_
    n_clases: int
    nombre_clase: str
    tipo: str


def ruta_modelo() -> Path:
    """Modelo que sirve la API: la versión ACTIVA del registro (panel MLOps) o, si no hay, MODELO_PATH."""
    from app.services.modelos import ruta_activa  # import perezoso: modelos.py importa este módulo

    activa = ruta_activa()
    if activa is not None:
        return activa
    p = Path(settings.MODELO_PATH)
    return p if p.is_absolute() else RAIZ_BACKEND / p


def _columnas_de_entrada(objeto: Any, estimador: Any) -> list[str] | None:
    for obj in (objeto, estimador):
        cols = getattr(obj, "feature_names_in_", None)
        if cols is not None:
            return [str(c) for c in cols]
    cols = getattr(estimador, "feature_name_", None)  # API sklearn de LightGBM
    if cols:
        return [str(c) for c in cols]
    get_booster = getattr(estimador, "get_booster", None)  # XGBoost
    if get_booster is not None and get_booster().feature_names:
        return [str(c) for c in get_booster().feature_names]
    return None


def cargar_modelo() -> ModeloCargado:
    """Modelo vigente. La caché va por (ruta, fecha del archivo): al activar otra versión o reemplazar el archivo
    se recarga sola, sin reiniciar el servidor."""
    ruta = ruta_modelo()
    mtime = ruta.stat().st_mtime_ns if ruta.is_file() else 0
    return cargar_modelo_de(ruta, mtime)


# lru_cache NO guarda excepciones: si el modelo aún no estaba, basta con copiarlo; no hace falta reiniciar.
@lru_cache(maxsize=2)
def cargar_modelo_de(ruta: Path, _mtime_ns: int = 0) -> ModeloCargado:
    if not ruta.is_file():
        raise ModeloNoDisponible("archivo_ausente")
    try:
        import joblib
        import shap
    except ImportError as exc:
        log.error("Faltan librerías de explicabilidad (shap/joblib): %s", exc)
        raise ModeloNoDisponible("dependencias") from exc

    try:
        # SEGURIDAD: joblib/pickle EJECUTA CÓDIGO al cargar. Solo se abre el archivo que tú despliegas en el
        # servidor (ruta fija en la configuración); jamás un archivo subido ni una ruta recibida en una petición.
        objeto = joblib.load(ruta)

        es_pipeline = hasattr(objeto, "steps") and hasattr(objeto, "predict")
        estimador = objeto.steps[-1][1] if es_pipeline else objeto
        pre = objeto[:-1] if es_pipeline and len(objeto.steps) > 1 else None

        columnas = _columnas_de_entrada(objeto, estimador)
        if not columnas:
            log.error("El modelo no expone los nombres de sus columnas de entrada")
            raise ModeloNoDisponible("configuracion")
        nombres = list(pre.get_feature_names_out()) if pre is not None else list(columnas)

        idx = None
        n_clases = 0
        clases = getattr(estimador, "classes_", None)
        if clases is not None:
            etiquetas = [str(c) for c in clases]
            n_clases = len(etiquetas)
            if settings.MODELO_CLASE_RIESGO not in etiquetas:
                log.error("MODELO_CLASE_RIESGO=%r no está en classes_=%s", settings.MODELO_CLASE_RIESGO, etiquetas)
                raise ModeloNoDisponible("configuracion")
            idx = etiquetas.index(settings.MODELO_CLASE_RIESGO)

        return ModeloCargado(
            estimador=estimador,
            preprocesador=pre,
            explainer=shap.TreeExplainer(estimador),
            columnas=tuple(columnas),
            nombres_modelo=tuple(str(n) for n in nombres),
            idx_clase=idx,
            n_clases=n_clases,
            nombre_clase=settings.MODELO_CLASE_RIESGO,
            tipo=type(estimador).__name__,
        )
    except ModeloNoDisponible:
        raise
    except Exception as exc:  # pickle de otra versión, estimador no soportado por TreeExplainer, etc.
        log.exception("No se pudo cargar el modelo de %s", ruta.name)
        raise ModeloNoDisponible("carga") from exc


cargar_modelo.cache_clear = cargar_modelo_de.cache_clear  # compatibilidad con el uso anterior


def precalentar() -> None:
    """Carga el modelo en segundo plano al arrancar: así la primera consulta del auditor no espera segundos."""
    try:
        cargar_modelo()
        log.info("Modelo de explicabilidad listo")
    except ModeloNoDisponible as exc:
        log.info("Explicabilidad sin precalentar (%s)", exc.motivo)


# ------------------------------------------------------------------ cálculo

def _sigmoide(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _finito(x: Any) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _valores_clase(sv: Any, m: ModeloCargado):
    """
    Normaliza la salida de SHAP, que cambia según el modelo y la versión de la librería:
      - lista [clase0, clase1, ...]  (versiones antiguas / multiclase)
      - matriz (muestras, variables) para modelos binarios de LightGBM/XGBoost/GradientBoosting: explica la clase 1
      - tensor (muestras, variables, clases) para RandomForest y otros
    Devuelve (valores de la clase de riesgo, signo): -1 si hubo que invertir una matriz binaria 2D.
    """
    import numpy as np

    signo = 1.0
    if isinstance(sv, list):
        arr = np.asarray(sv[m.idx_clase if m.idx_clase is not None else 0])
    else:
        arr = np.asarray(sv)
        if arr.ndim == 3:
            arr = arr[:, :, m.idx_clase if m.idx_clase is not None else 0]
        elif m.n_clases == 2 and m.idx_clase == 0:
            signo = -1.0  # la matriz 2D explica la clase 1; la clase 0 es su opuesta
    return arr[0].astype(float) * signo, signo


def _base_clase(expected: Any, m: ModeloCargado, signo: float) -> float:
    import numpy as np

    arr = np.atleast_1d(np.asarray(expected, dtype=float))
    return float(arr[m.idx_clase] if len(arr) > 1 and m.idx_clase is not None else arr[0]) * signo


def _variable_original(nombre: str, columnas: tuple[str, ...]) -> str:
    """
    Tras un OneHotEncoder una variable se reparte en varias columnas ("cat__regimen_nrus"). Como los valores
    SHAP son ADITIVOS, la contribución de la variable original es la suma de las de sus columnas.
    """
    if nombre in columnas:
        return nombre
    resto = nombre.split("__", 1)[-1]
    candidatas = [c for c in columnas if resto == c or resto.startswith(c + "_")]
    return max(candidatas, key=len) if candidatas else nombre


_ETIQUETAS_FEATURE = {
    "tipo_contribuyente": "Personería jurídica",
    "sector_economico": "Subsector comercial",
    "antiguedad_anos": "Antigüedad del negocio",
    "numero_empleados_formales": "Trabajadores formales",
    "ingresos_declarados": "Ingresos brutos anuales",
    "gastos_deducibles": "Costos y gastos declarados",
    "ratio_gastos_ingresos": "Ratio gastos / ingresos",
    "margen_utilidad_declarado": "Margen de utilidad declarado",
    "porcentaje_efectivo": "Ventas en efectivo",
    "facturas_anuladas": "Comprobantes anulados",
    "porcentaje_notas_credito": "Notas de crédito",
    "compras_proveedores_nuevos_pct": "Compras a proveedores nuevos",
    "concentracion_cliente_principal": "Concentración en cliente principal",
    "historial_auditoria": "Historial de auditoría",
    "retraso_declaracion_dias": "Días de retraso en declaraciones",
    "declaraciones_rectificatorias": "Declaraciones rectificatorias",
}

_FEATURE_A_PREGUNTA = {
    "tipo_contribuyente": "var_1_personeria_juridica",
    "sector_economico": "var_2_subsector_comercial",
    "antiguedad_anos": "var_3_antiguedad",
    "numero_empleados_formales": "var_4_trabajadores",
    "ingresos_declarados": "var_5_ingresos_brutos",
    "gastos_deducibles": "var_6_costos_gastos",
    "porcentaje_efectivo": "var_7_porcentaje_efectivo",
    "facturas_anuladas": "var_8_comprobantes_anulados",
    "porcentaje_notas_credito": "var_9_notas_credito",
    "compras_proveedores_nuevos_pct": "var_10_proveedores_nuevos",
    "concentracion_cliente_principal": "var_11_cliente_principal",
    "historial_auditoria": "var_12_resultado_auditoria",
    "retraso_declaracion_dias": "var_13_dias_mora",
    "declaraciones_rectificatorias": "var_14_rectificatorias",
}

_DERIVADAS_INGRESOS = {"ratio_gastos_ingresos", "margen_utilidad_declarado"}


def _etiqueta(variable: str) -> str:
    if variable in _ETIQUETAS_FEATURE:
        return _ETIQUETAS_FEATURE[variable]
    p = _PREGUNTAS.get(variable)
    if p:
        return p.get("corta") or p["texto"]
    return variable.replace("_", " ").capitalize()


def _valor_legible(variable: str, respuestas: dict, X) -> Any:
    pregunta_id = _FEATURE_A_PREGUNTA.get(variable)
    if pregunta_id and respuestas.get(pregunta_id) is not None:
        return str(respuestas[pregunta_id])

    if variable in respuestas and respuestas[variable] is not None:
        v = respuestas[variable]
        if variable == "sector_economico":
            return etiqueta_sector(str(v))
        return v if isinstance(v, (int, float, str)) and not isinstance(v, bool) else str(v)

    if variable in X.columns:
        if variable in _DERIVADAS_INGRESOS and "ratio_gastos_ingresos" in X.columns:
            ratio = _finito(X.iloc[0]["ratio_gastos_ingresos"])
            if ratio is not None and ratio < 0:
                return "No aplica"
        x = X.iloc[0][variable]
        if isinstance(x, str):
            return etiqueta_sector(x) if variable == "sector_economico" else x
        val = _finito(x)
        return round(val, 4) if val is not None else None
    return None

def explicar(respuestas: dict, max_display: int = 12) -> dict:
    """Contribuciones SHAP de UNA evaluación, ordenadas por magnitud (como el waterfall de shap)."""
    import numpy as np

    from app.services.features import construir_features  # puede lanzar FeaturesFaltantes

    m = cargar_modelo()
    X = construir_features(respuestas, list(m.columnas), como_categoria=m.preprocesador is None)
    if m.preprocesador is not None:
        Xt = m.preprocesador.transform(X)
        Xt = np.asarray(Xt.toarray() if hasattr(Xt, "toarray") else Xt, dtype=float)
    else:
        Xt = X

    valores, signo = _valores_clase(m.explainer.shap_values(Xt), m)
    base = _base_clase(m.explainer.expected_value, m, signo)
    total = base + float(valores.sum())  # f(x) en el espacio nativo del modelo

    # ¿En qué unidades están los valores? Se comprueba contra la probabilidad real del modelo (no se asume).
    p_modelo = None
    if m.idx_clase is not None and hasattr(m.estimador, "predict_proba"):
        p_modelo = float(m.estimador.predict_proba(Xt)[0, m.idx_clase])
    espacio = "desconocido"
    if p_modelo is not None:
        if abs(total - p_modelo) < 1e-4:
            espacio = "probabilidad"
        elif abs(_sigmoide(total) - p_modelo) < 1e-4:
            espacio = "log-odds"
        else:
            log.warning("SHAP no cuadra con predict_proba (total=%.6f, p=%.6f)", total, p_modelo)

    acumulado: dict[str, float] = {}
    for nombre, v in zip(m.nombres_modelo, valores):
        var = _variable_original(nombre, m.columnas)
        acumulado[var] = acumulado.get(var, 0.0) + float(v)
    filas = [
        {"variable": var, "etiqueta": _etiqueta(var), "valor": _valor_legible(var, respuestas, X), "shap": s}
        for var, s in acumulado.items()
    ]
    filas.sort(key=lambda f: abs(f["shap"]), reverse=True)
    visibles, resto = filas[:max_display], filas[max_display:]

    return {
        "modelo": m.tipo,
        "clase_riesgo": m.nombre_clase,
        "espacio": espacio,
        "valor_base": base,
        "prediccion": total,
        "probabilidad_base": _sigmoide(base) if espacio == "log-odds" else (base if espacio == "probabilidad" else None),
        "probabilidad": p_modelo,
        "contribuciones": visibles,
        # Igual que shap.plots.waterfall: lo que no cabe se agrupa en una sola barra "otras variables".
        "otras": {"cantidad": len(resto), "shap": sum(f["shap"] for f in resto)} if resto else None,
    }
