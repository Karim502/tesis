-- Módulo Administrador (RBAC, MLOps y bitácora). Ejecutar UNA vez:  psql -d tesis_mype -f sql/005_admin_mlops.sql
-- Idempotente. Requiere 002–004 aplicadas antes.
BEGIN;

-- 1) Tabla de usuarios: el rol ya existe (usuarios.rol). Se refuerza su integridad y se agrega el índice que usa el panel.
ALTER TABLE usuarios ALTER COLUMN rol    SET NOT NULL;
ALTER TABLE usuarios ALTER COLUMN activo SET NOT NULL;
ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS ck_usuarios_rol;
ALTER TABLE usuarios ADD CONSTRAINT ck_usuarios_rol CHECK (rol IN ('DUENO_MYPE', 'AUDITOR', 'ADMIN'));
CREATE INDEX IF NOT EXISTS idx_usuarios_rol_activo ON usuarios (rol, activo);

-- 2) Bitácora de auditoría (solo inserciones). La FK es SET NULL: el correo/rol quedan congelados en la propia fila.
CREATE TABLE IF NOT EXISTS audit_logs (
    id            BIGSERIAL    PRIMARY KEY,
    creado_en     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    usuario_id    BIGINT       REFERENCES usuarios(id) ON DELETE SET NULL,
    usuario_email VARCHAR(255),
    usuario_rol   VARCHAR(20),
    accion        VARCHAR(40)  NOT NULL,
    recurso_tipo  VARCHAR(30),
    recurso_id    BIGINT,
    detalle       JSONB,
    ip            VARCHAR(45)
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_fecha          ON audit_logs (creado_en DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_usuario_fecha  ON audit_logs (usuario_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_accion_fecha   ON audit_logs (accion, creado_en DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_recurso        ON audit_logs (recurso_tipo, recurso_id);

-- 3) Historial de versiones del modelo
CREATE TABLE IF NOT EXISTS model_versions (
    id             BIGSERIAL    PRIMARY KEY,
    version        INTEGER      NOT NULL UNIQUE,
    archivo        VARCHAR(120) NOT NULL,
    estado         VARCHAR(12)  NOT NULL DEFAULT 'ENTRENANDO'
                   CHECK (estado IN ('ENTRENANDO', 'CANDIDATO', 'ACTIVO', 'ARCHIVADO', 'FALLIDO')),
    etapa          VARCHAR(40),
    accuracy       DOUBLE PRECISION,
    f1_score       DOUBLE PRECISION,
    "precision"    DOUBLE PRECISION,
    recall         DOUBLE PRECISION,
    roc_auc        DOUBLE PRECISION,
    n_filas_train  INTEGER,
    n_filas_test   INTEGER,
    origen_datos   VARCHAR(200),
    hiperparametros JSONB,
    sha256         VARCHAR(64),
    error          TEXT,
    iniciado_por   BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    finalizado_en  TIMESTAMPTZ,
    activado_en    TIMESTAMPTZ,
    activado_por   BIGINT REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_model_versions_creado ON model_versions (creado_en DESC);
-- Reglas garantizadas por la BD: un solo modelo ACTIVO y un solo entrenamiento EN CURSO.
CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_un_activo     ON model_versions (estado) WHERE estado = 'ACTIVO';
CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_un_entrenando ON model_versions (estado) WHERE estado = 'ENTRENANDO';

COMMIT;
