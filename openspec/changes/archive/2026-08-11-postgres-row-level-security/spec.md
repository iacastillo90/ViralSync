# OpenSpec Spec: PostgreSQL Row Level Security (RLS) Multi-Tenant Isolation

## Requirements & Scenarios

### REQ-RLS-01: Migración y Declaración de Políticas RLS
- **Scenario 1:** La migración `006_enable_rls.sql` habilita RLS en las tablas `videos`, `ideas`, `leads`, `products` y `metrics`.
- **Scenario 2:** Las políticas evalúan `tenant_id = current_setting('app.current_tenant_id', true)`.

### REQ-RLS-02: Contexto de Sesión de Base de Datos
- **Scenario 1:** Al ejecutar `set_tenant_session_context(session, "tenant_a")`, la sesión async ejecuta `SET LOCAL app.current_tenant_id = 'tenant_a'`.
- **Scenario 2:** Cualquier consulta SELECT/UPDATE/DELETE realizada en la sesión filtrará automáticamente solo las filas pertenecientes a `'tenant_a'`.
