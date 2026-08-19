-- =============================================================================
-- Migración 012: Personalización White-Label por Agencia (Marca Blanca)
-- =============================================================================

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS logo_url TEXT,
    ADD COLUMN IF NOT EXISTS primary_color VARCHAR(16) DEFAULT '#4F46E5',
    ADD COLUMN IF NOT EXISTS agency_name TEXT;

COMMENT ON COLUMN tenants.primary_color IS 'Color primario hexadecimal para la interfaz y reportes PDF de marca blanca.';
