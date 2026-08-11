# OpenSpec Spec: Pruebas de Carga y Estrés con Locust

## Requirements & Scenarios

### REQ-LLT-01: Simulación de Carga Multi-Tenant Concurrente
- **Scenario 1:** Un enjambre de 100 usuarios Locust ejecuta solicitudes `/health`, `/graph/run` y `/ideas` simultáneamente.
- **Scenario 2:** El rate limiter bloquea las solicitudes que exceden la cuota per-tenant devolviendo HTTP 429.

### REQ-LLT-02: Verificación de Latencia P95
- **Scenario 1:** Las respuestas del API backend mantienen un P95 < 200ms para endpoints de consulta sin degradación de base de datos.
