-- CU01: historial de evaluaciones (incluye Modo Invitado). Ejecutar después de schema.sql
-- Si tu tabla ya existía SIN is_guest, ejecuta en su lugar sql/002_modo_invitado.sql
CREATE TABLE IF NOT EXISTS evaluaciones (
    id              BIGSERIAL    PRIMARY KEY,
    user_id         BIGINT       REFERENCES usuarios(id) ON DELETE CASCADE,   -- NULL => invitado
    is_guest        BOOLEAN      NOT NULL DEFAULT FALSE,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    respuestas      JSONB        NOT NULL,
    nivel_riesgo    VARCHAR(10)  NOT NULL CHECK (nivel_riesgo IN ('Bajo', 'Medio', 'Alto')),
    probabilidad    DOUBLE PRECISION NOT NULL CHECK (probabilidad BETWEEN 0 AND 1),  -- prob. de incumplimiento
    score           INTEGER      NOT NULL CHECK (score BETWEEN 0 AND 100),           -- puntaje de cumplimiento
    recomendaciones JSONB        NOT NULL DEFAULT '[]'::jsonb,                        -- checklist con su avance
    CONSTRAINT ck_evaluaciones_guest_consistente
        CHECK ((is_guest AND user_id IS NULL) OR (NOT is_guest AND user_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_user_fecha ON evaluaciones (user_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_is_guest   ON evaluaciones (is_guest);
