-- =============================================================================
-- Migración 010: A/B Testing de Ganchos Virales (ViralSync Enterprise)
-- =============================================================================
-- Crea la tabla `script_variants` para comparar variantes de ganchos A/B y medir
-- su desempeño relativo a las 72h.
-- =============================================================================

CREATE TABLE IF NOT EXISTS script_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    variant_label VARCHAR(10) NOT NULL DEFAULT 'B',
    gancho_0_5s_variant TEXT NOT NULL,
    views_72h INTEGER DEFAULT 0,
    conversion_72h INTEGER DEFAULT 0,
    winner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_script_variants_script ON script_variants (script_id, tenant_id);

COMMENT ON TABLE script_variants IS 'Tabla de variantes A/B de ganchos virales para experimentos de retención a las 72h.';
