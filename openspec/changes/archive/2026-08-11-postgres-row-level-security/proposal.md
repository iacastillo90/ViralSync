# OpenSpec Proposal: PostgreSQL Row Level Security (RLS) Multi-Tenant Isolation

- **Change ID:** `postgres-row-level-security`
- **Scope:** Habilitar Row Level Security (RLS) en el motor de PostgreSQL para las tablas multi-tenant e integrar la variable de sesión `SET LOCAL app.current_tenant_id` en SQLAlchemy.

## Problem Statement
Actualmente el aislamiento de datos entre tenants depende únicamente del filtrado en las consultas SQL construidas en el código Python (`WHERE tenant_id = :tenant_id`). Si en el futuro un desarrollador omite esa cláusula en una consulta o DAO, se produciría una fuga de datos entre tenants sin que el motor de base de datos lo prevenga.

## Proposed Solution
1. **Migración SQL (`migrations/006_enable_rls.sql`):**
   - Habilitar RLS en `videos`, `ideas`, `leads`, `products` y `metrics` vía `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`.
   - Crear políticas de seguridad: `CREATE POLICY tenant_isolation_policy ON ... USING (tenant_id = current_setting('app.current_tenant_id', true));`.
2. **Contexto de Sesión Async (`backend/db/session.py`):**
   - Crear una función helper `set_tenant_session_context(session: AsyncSession, tenant_id: str)` que ejecute `SET LOCAL app.current_tenant_id = :tenant_id` garantizando aislamiento criptográfico e inquebrantable a nivel de motor de BD.
