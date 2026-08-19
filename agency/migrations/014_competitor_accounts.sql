-- agency/migrations/014_competitor_accounts.sql
-- Migración SQL 014 (S4 — Competitor Benchmark, REQ-COMP-01): catálogo de cuentas
-- competidoras por tenant para la ingestión de hooks y el benchmark propios vs ajenos.
-- Idempotente (patrón IF NOT EXISTS de 002). Aplica sobre el schema previo:
--   - competitor_accounts (id, tenant_id FK CASCADE, platform, username,
--     display_name, niche, is_active, created_at)
--   - idx_competitor_accounts_tenant (tenant_id, is_active) para listar/filtrar
--     cuentas activas por tenant (REQ-COMP-04 escenario 2).

CREATE TABLE IF NOT EXISTS competitor_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform TEXT NOT NULL DEFAULT 'instagram',
    username TEXT NOT NULL,
    display_name TEXT,
    niche TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_competitor_accounts_tenant ON competitor_accounts (tenant_id, is_active);