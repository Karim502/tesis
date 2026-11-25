"""Historial de versiones del modelo predictivo (LightGBM) para trazabilidad y reversión."""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EstadoModelo(str, enum.Enum):
    ENTRENANDO = "ENTRENANDO"   # job en curso
    CANDIDATO = "CANDIDATO"     # entrenado y con métricas, aún NO sirve predicciones/SHAP
    ACTIVO = "ACTIVO"           # el que usa la API (solo uno a la vez)
    ARCHIVADO = "ARCHIVADO"     # fue activo y lo reemplazó otro; se puede reactivar (rollback)
    FALLIDO = "FALLIDO"         # el entrenamiento terminó con error


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        # Garantías a nivel de BASE DE DATOS (valen aunque haya varios workers o dos clics simultáneos):
        #  · máximo UN entrenamiento en curso, y
        #  · máximo UN modelo activo.
        Index("uq_model_versions_un_entrenando", "estado", unique=True,
              postgresql_where=text("estado = 'ENTRENANDO'"), sqlite_where=text("estado = 'ENTRENANDO'")),
        Index("uq_model_versions_un_activo", "estado", unique=True,
              postgresql_where=text("estado = 'ACTIVO'"), sqlite_where=text("estado = 'ACTIVO'")),
        Index("idx_model_versions_creado", "creado_en"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)            # 1, 2, 3… => modelo_v{version}.joblib
    archivo: Mapped[str] = mapped_column(String(120))                    # solo el NOMBRE; la carpeta sale de la configuración
    estado: Mapped[str] = mapped_column(String(12), default=EstadoModelo.ENTRENANDO.value)
    etapa: Mapped[str | None] = mapped_column(String(40))                # texto de progreso mientras entrena

    # Métricas sobre el conjunto de prueba (holdout) que el modelo NO vio al entrenar.
    accuracy: Mapped[float | None] = mapped_column(Float)
    f1_score: Mapped[float | None] = mapped_column(Float)
    precision: Mapped[float | None] = mapped_column(Float)
    recall: Mapped[float | None] = mapped_column(Float)
    roc_auc: Mapped[float | None] = mapped_column(Float)

    n_filas_train: Mapped[int | None] = mapped_column(Integer)
    n_filas_test: Mapped[int | None] = mapped_column(Integer)
    origen_datos: Mapped[str | None] = mapped_column(String(200))        # p. ej. "lote subido: datos.csv" / "dataset por defecto"
    hiperparametros: Mapped[dict | None] = mapped_column(JSONB)
    sha256: Mapped[str | None] = mapped_column(String(64))               # huella del .joblib: detecta archivos alterados
    error: Mapped[str | None] = mapped_column(Text)                      # mensaje corto y controlado (el detalle va al log)

    iniciado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="SET NULL"))
