-- Gestión de auditoría: ejecutar UNA vez sobre la BD existente.
--   psql -d tesis_mype -f sql/003_auditoria.sql
-- Idempotente. Las evaluaciones existentes (incluidas las de invitados) quedan como 'PENDIENTE'.
BEGIN;

ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS estado_auditoria VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE';
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS notas_auditor    TEXT;
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS auditado_por     BIGINT REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS auditado_en      TIMESTAMPTZ;

ALTER TABLE evaluaciones DROP CONSTRAINT IF EXISTS ck_evaluaciones_estado_auditoria;
ALTER TABLE evaluaciones ADD CONSTRAINT ck_evaluaciones_estado_auditoria
    CHECK (estado_auditoria IN ('PENDIENTE', 'EN_REVISION', 'CERRADO'));

CREATE INDEX IF NOT EXISTS idx_evaluaciones_estado_fecha ON evaluaciones (estado_auditoria, creado_en DESC);
COMMIT;
