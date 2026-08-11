-- 006_enable_rls.sql: Habilitación de Row Level Security (RLS) en PostgreSQL
-- Garantiza aislamiento multi-tenant nativo a nivel de motor de BD.

-- 1. Habilitar RLS en tablas multi-tenant
ALTER TABLE ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- 2. Crear políticas de aislamiento por tenant_id

DROP POLICY IF EXISTS tenant_isolation_ideas ON ideas;
CREATE POLICY tenant_isolation_ideas ON ideas
    USING (tenant_id = current_setting('app.current_tenant_id', true));

DROP POLICY IF EXISTS tenant_isolation_videos ON videos;
CREATE POLICY tenant_isolation_videos ON videos
    USING (tenant_id = current_setting('app.current_tenant_id', true));

DROP POLICY IF EXISTS tenant_isolation_leads ON leads;
CREATE POLICY tenant_isolation_leads ON leads
    USING (tenant_id = current_setting('app.current_tenant_id', true));

DROP POLICY IF EXISTS tenant_isolation_products ON products;
CREATE POLICY tenant_isolation_products ON products
    USING (tenant_id = current_setting('app.current_tenant_id', true));
