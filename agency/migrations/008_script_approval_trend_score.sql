-- =============================================================================
-- Migración 008: Aprobación de Guiones y Scoring de Tendencias
-- =============================================================================
-- Agrega a la tabla `scripts`:
--   - approval_status : estado de aprobación del guion (pending | approved | rejected)
--   - trend_score     : puntuación de impacto viral 0-100 generada por el motor híbrido
--   - trend_rationale : justificación legible del score (generada por Gemini)
-- =============================================================================

ALTER TABLE scripts
    ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    ADD COLUMN IF NOT EXISTS trend_score     NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS trend_rationale TEXT;

-- Índice para acelerar las consultas "dame los guiones aprobados de este tenant"
CREATE INDEX IF NOT EXISTS idx_scripts_tenant_approval
    ON scripts (tenant_id, approval_status);

COMMENT ON COLUMN scripts.approval_status IS
    'Estado de aprobación del guion: pending = en espera, approved = aprobado por cliente, rejected = descartado.';

COMMENT ON COLUMN scripts.trend_score IS
    'Score de impacto viral 0-100 calculado por el motor híbrido (LLM Gemini + reglas de tendencias).';

COMMENT ON COLUMN scripts.trend_rationale IS
    'Justificación en lenguaje natural del trend_score generada por Gemini (máx. 300 chars).';
