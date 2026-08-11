# OpenSpec Proposal: OpenTelemetry, Sentry & LiteLLM Observability

- **Change ID:** `opentelemetry-sentry-observability`
- **Scope:** Instrumentación de observabilidad de nivel enterprise para trazabilidad de latencias HTTP/SQL (OpenTelemetry), captura de excepciones en producción (Sentry) y auditoría de costos de modelos LLM por tenant (LiteLLM Gateway).

## Problem Statement
Actualmente el diagnóstico de problemas en producción depende exclusivamente de logs de texto en consola (`stdout`). No existe rastreo de latencias de red/base de datos entre microservicios (Distributed Tracing), captura automática de stack traces en producción, ni visibilidad del gasto exacto en dólares de llamadas a LLM por cada `tenant_id`.

## Proposed Solution
1. **Módulo de Observabilidad (`backend/observability.py`):**
   - Crear `setup_observability(app: FastAPI)` que inicialice opcionalmente OpenTelemetry (`opentelemetry-sdk`) y Sentry (`sentry-sdk`) si están configurados en variables de entorno (`SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT`), con fallback seguro si no están presentes.
2. **Configuración de Gateway LiteLLM (`gateway/litellm_config.production.yaml`):**
   - Habilitar callbacks de supervisión (`langsmith`, `prometheus` o `success_callbacks`) para auditar consumo de tokens y costo en dólares por tenant.
3. **Integración en FastAPI (`backend/main.py`):**
   - Invocar `setup_observability` al inicio de la aplicación FastAPI.
