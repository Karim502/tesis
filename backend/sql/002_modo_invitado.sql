-- Modo Invitado: ejecutar UNA vez sobre la BD existente.
--   psql -d tesis_mype -f sql/002_modo_invitado.sql
-- Es idempotente: puedes volver a correrla sin dañar nada.
BEGIN;

ALTER TABLE evaluaciones ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS is_guest BOOLEAN NOT NULL DEFAULT FALSE;

-- Los registros previos son todos de usuarios con cuenta (is_guest = FALSE por defecto),
-- así que la restricción se cumple desde el primer momento.
ALTER TABLE evaluaciones DROP CONSTRAINT IF EXISTS ck_evaluaciones_guest_consistente;
ALTER TABLE evaluaciones ADD CONSTRAINT ck_evaluaciones_guest_consistente
    CHECK ((is_guest AND user_id IS NULL) OR (NOT is_guest AND user_id IS NOT NULL));

CREATE INDEX IF NOT EXISTS idx_evaluaciones_is_guest ON evaluaciones (is_guest);
COMMIT;
