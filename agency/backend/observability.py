"""
observability.py

Módulo de inicialización de observabilidad Enterprise para ViralSync (REQ-OBS-01).
Soporta Sentry SDK para error tracking y OpenTelemetry para Distributed Tracing
con fallback seguro si los servicios no están configurados.
"""

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

def setup_observability(app: Any = None) -> dict:
    """Inicializa Sentry y OpenTelemetry si las variables de entorno están presentes."""
    status = {"sentry_enabled": False, "opentelemetry_enabled": False}
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    agency_env = os.getenv("AGENCY_ENV", "dev").lower()

    # 1. Configurar Sentry Error Tracking
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=agency_env,
                traces_sample_rate=1.0 if agency_env == "dev" else 0.2,
            )
            status["sentry_enabled"] = True
            logger.info(f"[Observability] Sentry SDK inicializado en entorno '{agency_env}'")
        except Exception as exc:
            logger.warning(f"[Observability] No se pudo inicializar Sentry ({exc})")

    # 2. Configurar OpenTelemetry Tracing
    if otel_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            
            provider = TracerProvider()
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint))
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            status["opentelemetry_enabled"] = True
            logger.info(f"[Observability] OpenTelemetry TracerProvider conectado a '{otel_endpoint}'")
        except Exception as exc:
            logger.warning(f"[Observability] No se pudo inicializar OpenTelemetry ({exc})")


    if not status["sentry_enabled"] and not status["opentelemetry_enabled"]:
        logger.info("[Observability] Modo local/dev: Sentry y OpenTelemetry inactivos (sin DSN/Endpoint).")

    return status
