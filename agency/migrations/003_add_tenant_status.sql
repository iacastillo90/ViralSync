-- agency/migrations/003_add_tenant_status.sql
-- Migración SQL 003: Columna `status` para la tabla tenants.
-- El ORM (backend/db/models.py Tenant) la declara con default 'active' y los routers
-- de tenant admin la leen/actualizan (list_tenants, get_tenant, create_tenant).
-- Sin esta columna, el INSERT del onboarding (Tenant.status) falla con
-- UndefinedColumn sobre el esquema de migración — mismo patrón que 002 con leads.
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';