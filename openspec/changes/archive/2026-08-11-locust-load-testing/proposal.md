# OpenSpec Proposal: Pruebas de Carga y Estrés con Locust

- **Change ID:** `locust-load-testing`
- **Scope:** Suite de pruebas de carga en `agency/tests/load/locustfile.py` para verificar concurrencia de 100 usuarios en `/graph/run`, `/ideas/approve`, SSE y Rate Limiting.

## Problem Statement
A medida que la plataforma escala a multi-tenant enterprise, necesitamos garantizar que el rate limiter, Celery, Redis y PostgreSQL RLS soporten concurrencia sin cuellos de botella ni deadlocks en las transacciones DB.

## Proposed Solution
1. Crear `agency/tests/load/locustfile.py` definiendo escenarios de usuario (`HttpUser` / `FastHttpUser`).
2. Probar escenarios de ejecuciones concurrentes, aprobaciones de ideas, sondeos de salud y streaming de SSE.
3. Verificar que el rate limiter devuelva HTTP 429 con cabecera `Retry-After: 60` ante picos de tráfico.
