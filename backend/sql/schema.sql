-- Esquema mínimo para CU04. Ejecutar:  psql -U tesis_user -d tesis_mype -f sql/schema.sql
CREATE EXTENSION IF NOT EXISTS citext;  -- correos sin distinción de mayúsculas

CREATE TABLE IF NOT EXISTS usuarios (
    id            BIGSERIAL    PRIMARY KEY,
    nombre        VARCHAR(120) NOT NULL,
    email         CITEXT       NOT NULL UNIQUE,
    password_hash VARCHAR(100) NOT NULL,          -- hash bcrypt (60 chars), jamás la contraseña
    rol           VARCHAR(20)  NOT NULL
                  CHECK (rol IN ('DUENO_MYPE', 'AUDITOR', 'ADMIN')),
    activo        BOOLEAN      NOT NULL DEFAULT TRUE,
    ultimo_login  TIMESTAMPTZ,
    creado_en     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
