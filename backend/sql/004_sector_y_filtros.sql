-- Sector económico + índices de los filtros avanzados. Ejecutar UNA vez (idempotente):
--   psql -d tesis_mype -f sql/004_sector_y_filtros.sql
BEGIN;

ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS sector_economico VARCHAR(40);

-- Rellena la columna con la respuesta ya guardada (si el cuestionario ya incluía el sector).
UPDATE evaluaciones
   SET sector_economico = respuestas->>'sector_economico'
 WHERE sector_economico IS NULL AND respuestas->>'sector_economico' IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_evaluaciones_sector       ON evaluaciones (sector_economico);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_probabilidad ON evaluaciones (probabilidad);
COMMIT;
