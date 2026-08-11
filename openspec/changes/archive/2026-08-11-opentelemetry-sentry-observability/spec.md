# OpenSpec Spec: OpenTelemetry, Sentry & LiteLLM Observability

## Requirements & Scenarios

### REQ-OBS-01: Inicialización Resiliente de Observabilidad
- **Scenario 1:** Cuando `SENTRY_DSN` está presente en el entorno, `setup_observability` inicializa `sentry_sdk.init()`.
- **Scenario 2:** En ausencia de `SENTRY_DSN` u `OTEL_EXPORTER_OTLP_ENDPOINT` (entorno local dev), la aplicación arranca normalmente emitiendo un log informativo sin lanzar excepciones.

### REQ-OBS-02: Auditoría de Costo LLM en LiteLLM Gateway
- **Scenario 1:** Las configuraciones `litellm_config.production.yaml` y `litellm_config.staging.yaml` declaran parámetros de observabilidad y trackean la metadata `tenant_id` en las respuestas de la API.
