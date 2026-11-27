import io
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.model_version import EstadoModelo, ModelVersion
from app.services import modelos
from app.services.explicabilidad import RAIZ_BACKEND, ModeloNoDisponible, cargar_modelo
from app.services.almacenamiento import publicar

log = logging.getLogger(__name__)

HIPERPARAMETROS = dict(
    n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=5,
    class_weight="balanced", random_state=42, n_jobs=1, verbose=-1,
)
MIN_POR_CLASE = 6

NUM_COLS = [
    "antiguedad_anos", "numero_empleados_formales", "ingresos_declarados",
    "gastos_deducibles", "ratio_gastos_ingresos", "porcentaje_efectivo",
    "margen_utilidad_declarado", "facturas_anuladas", "porcentaje_notas_credito",
    "compras_proveedores_nuevos_pct", "concentracion_cliente_principal",
    "retraso_declaracion_dias", "declaraciones_rectificatorias",
]
CAT_COLS = ["tipo_contribuyente", "sector_economico", "historial_auditoria"]


class DatosInvalidos(Exception):
    """Problema del lote de datos que el administrador puede corregir."""


def ruta_dataset_defecto() -> Path:
    p = Path(settings.ENTRENAMIENTO_CSV_PATH)
    return p if p.is_absolute() else RAIZ_BACKEND / p


def _columnas_de_entrada(df, objetivo: str) -> list[str]:
    if settings.ENTRENAMIENTO_FEATURES:
        cols = list(settings.ENTRENAMIENTO_FEATURES)
    else:
        try:
            cols = list(cargar_modelo().columnas)
        except ModeloNoDisponible:
            cols = [c for c in df.columns if c != objetivo]
    faltan = [c for c in cols if c not in df.columns]
    if faltan:
        raise DatosInvalidos("Al lote le faltan columnas que el modelo necesita: " + ", ".join(faltan) + ".")
    return cols


def cargar_lote(origen: Path | bytes):
    """Lee y VALIDA el CSV. Devuelve (X, y)."""
    import pandas as pd

    try:
        df = pd.read_csv(io.BytesIO(origen) if isinstance(origen, bytes) else origen)
    except Exception as exc:
        raise DatosInvalidos("No se pudo leer el archivo como CSV (UTF-8, separado por comas).") from exc

    objetivo = settings.ENTRENAMIENTO_TARGET
    if objetivo not in df.columns and "riesgo_evasion" in df.columns:
        objetivo = "riesgo_evasion"
    if objetivo not in df.columns:
        raise DatosInvalidos(f"Falta la columna objetivo «{settings.ENTRENAMIENTO_TARGET}» (valores 0 = cumple, 1 = riesgo).")

    y = pd.to_numeric(df[objetivo], errors="coerce")
    df, y = df[y.notna()], y[y.notna()]
    if not set(y.unique()) <= {0, 1}:
        raise DatosInvalidos(f"La columna «{objetivo}» solo puede contener 0 y 1.")
    y = y.astype(int)
    if len(df) < settings.ENTRENAMIENTO_MIN_FILAS:
        raise DatosInvalidos(f"El lote tiene {len(df)} filas válidas; se necesitan al menos {settings.ENTRENAMIENTO_MIN_FILAS}.")
    conteo = y.value_counts()
    if len(conteo) < 2 or conteo.min() < MIN_POR_CLASE:
        raise DatosInvalidos(f"Cada clase (0 y 1) necesita al menos {MIN_POR_CLASE} filas; el lote tiene {conteo.to_dict()}.")

    cols = _columnas_de_entrada(df, objetivo)
    X = df[cols].copy()
    for c in NUM_COLS:
        if c in X.columns:
            X[c] = pd.to_numeric(X[c], errors="coerce").fillna(-1)
    for c in CAT_COLS:
        if c in X.columns:
            X[c] = X[c].fillna("Desconocido").astype(str).str.strip()
    return X, y


def guardar_lote_subido(contenido: bytes, version: int) -> Path:
    carpeta = modelos.carpeta_modelos() / "lotes"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"lote_v{version}.csv"
    ruta.write_bytes(contenido)
    return ruta


def _etapa(db, v: ModelVersion, texto: str) -> None:
    v.etapa = texto
    db.commit()


def ejecutar_entrenamiento(version_id: int, ruta_csv: str, activar_si_mejora: bool, admin_id: int) -> None:
    """Tarea de fondo. Abre su PROPIA sesión de BD y no deja nunca la fila en ENTRENANDO."""
    with SessionLocal() as db:
        v = db.get(ModelVersion, version_id)
        if v is None:
            return
        destino: Path | None = None
        try:
            _etapa(db, v, "validando datos")
            X, y = cargar_lote(Path(ruta_csv))

            _etapa(db, v, "entrenando")
            import joblib
            from lightgbm import LGBMClassifier
            from sklearn.compose import ColumnTransformer
            from sklearn.model_selection import train_test_split
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import OneHotEncoder, StandardScaler

            X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

            preprocessor = ColumnTransformer(
                transformers=[
                    ("num", StandardScaler(), [c for c in NUM_COLS if c in X.columns]),
                    ("cat", OneHotEncoder(sparse_output=False, handle_unknown="ignore"), [c for c in CAT_COLS if c in X.columns]),                ]
            )
            modelo = Pipeline([
                ("prep", preprocessor),
                ("clf", LGBMClassifier(**HIPERPARAMETROS)),
            ]).fit(X_tr, y_tr)

            _etapa(db, v, "evaluando")
            from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

            pred = modelo.predict(X_te)
            v.accuracy = float(accuracy_score(y_te, pred))
            v.f1_score = float(f1_score(y_te, pred, zero_division=0))
            v.precision = float(precision_score(y_te, pred, zero_division=0))
            v.recall = float(recall_score(y_te, pred, zero_division=0))
            v.roc_auc = float(roc_auc_score(y_te, modelo.predict_proba(X_te)[:, 1])) if y_te.nunique() == 2 else None
            v.n_filas_train, v.n_filas_test = int(len(X_tr)), int(len(X_te))
            v.hiperparametros = HIPERPARAMETROS

            _etapa(db, v, "guardando")
            destino = modelos.ruta_de(v)
            destino.parent.mkdir(parents=True, exist_ok=True)
            tmp = destino.with_name(f".{destino.name}.{uuid.uuid4().hex}.tmp")
            joblib.dump(modelo, tmp)
            os.replace(tmp, destino)
            v.sha256 = modelos.sha256_de(destino)
            publicar(destino, v.sha256)

            v.estado, v.etapa = EstadoModelo.CANDIDATO.value, None
            v.finalizado_en = datetime.now(timezone.utc)
            db.commit()

            if activar_si_mejora:
                _promover_si_mejora(db, v, admin_id)
            log.info("Entrenamiento v%s terminado: F1=%.3f accuracy=%.3f", v.version, v.f1_score, v.accuracy)
        except DatosInvalidos as exc:
            _fallar(db, v, str(exc))
        except Exception:
            if destino is not None and destino.is_file():
                destino.unlink(missing_ok=True)
            log.exception("Falló el entrenamiento de la versión %s", v.version if v else version_id)
            _fallar(db, v, "Error interno durante el entrenamiento; revisa los logs del servidor.")


def _promover_si_mejora(db, nuevo: ModelVersion, admin_id: int) -> None:
    actual = modelos.version_activa(db)
    if actual is None or actual.f1_score is None or nuevo.f1_score is None or nuevo.f1_score <= actual.f1_score:
        return
    from app.models.audit_log import Accion
    from app.services.bitacora import registrar

    try:
        modelos.activar(db, nuevo, admin_id)
        registrar(db, None, Accion.MODELO_ACTIVADO, recurso_tipo="modelo", recurso_id=nuevo.id, commit=False,
                  detalle={"version": nuevo.version, "automatica": True, "f1_anterior": actual.f1_score, "f1_nuevo": nuevo.f1_score})
        db.commit()
    except modelos.ActivacionInvalida as exc:
        nid = nuevo.id
        db.rollback()
        nuevo = db.get(ModelVersion, nid)
        nuevo.error = f"No se activó automáticamente: {exc.message}"
        db.commit()


def _fallar(db, v: ModelVersion | None, mensaje: str) -> None:
    if v is None:
        return
    vid = v.id
    db.rollback()
    v = db.get(ModelVersion, vid)
    v.estado, v.etapa, v.error = EstadoModelo.FALLIDO.value, None, mensaje[:500]
    v.finalizado_en = datetime.now(timezone.utc)
    db.commit()