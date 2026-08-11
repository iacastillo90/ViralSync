# OpenSpec Spec: Redis Per-Tenant Rate Limiter

## Requirements & Scenarios

### REQ-RAT-01: Control de Tasa Per-Tenant
- **Scenario 1:** Cuando un `tenant_id` realiza peticiones por debajo del límite (ej. <= 30 peticiones/minuto), `check_rate_limit` devuelve `True` y la API responde HTTP 200/202.
- **Scenario 2:** Cuando las peticiones exceden el límite dentro de los 60 segundos, `check_rate_limit` devuelve `False` y la API retorna HTTP `429 Too Many Requests`.
- **Scenario 3:** Tras expirar el tiempo de la ventana (60s), el contador en Redis se reinicia automáticamente.
