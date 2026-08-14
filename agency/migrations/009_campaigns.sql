-- =============================================================================
-- Migración 009: Modo Campaña (ViralSync Enterprise)
-- =============================================================================
-- Crea la tabla `campaigns` para agrupar ideaciones, guiones y videos bajo un mismo objetivo comercial.
-- Agrega `campaign_id` a la tabla `ideas`.
-- =============================================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    objective TEXT,
    target_reels_count INTEGER DEFAULT 8,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_tenant ON campaigns (tenant_id, status);

ALTER TABLE ideas
    ADD COLUMN IF NOT EXISTS campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL;

COMMENT ON TABLE campaigns IS 'Tabla de Campañas Comerciales que agrupa múltiples piezas de contenido corto.';
