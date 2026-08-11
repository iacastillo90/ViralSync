# OpenSpec Proposal: Redis Per-Tenant Rate Limiter

- **Change ID:** `rate-limiting-redis`
- **Scope:** Protección de endpoints sensibles (`/graph/run`, `/ideas/approve`, `/publish/approve`) contra abuso de cuota LLM mediante Rate Limiting basado en Redis por `tenant_id` e IP.

## Problem Statement
Sin un control de tasa de peticiones, un cliente o un bucle en el frontend puede disparar cientos de ejecuciones de grafo por minuto en `/graph/run`, saturando la cola Celery y agotando el presupuesto de modelos de lenguaje en LiteLLM Gateway.

## Proposed Solution
1. Crear el módulo `backend/security/rate_limiter.py` con `check_rate_limit(tenant_id: str, limit: int, window_seconds: int) -> bool`.
2. Integrar la verificación en `/graph/run` lanzando un error HTTP `429 Too Many Requests` con la cabecera `Retry-After: 60` cuando un tenant exceda la cuota configurada (ej. 30 ejecuciones/minuto).
