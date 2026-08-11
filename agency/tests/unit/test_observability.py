"""
test_observability.py

Pruebas unitarias para verificar la inicialización resiliente de observabilidad (REQ-OBS-01).
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from backend.observability import setup_observability


def test_setup_observability_local_dev_fallback():
    """Verifica que sin variables SENTRY_DSN u OTEL el módulo no falle y reporte inactivo."""
    with patch.dict(os.environ, {"SENTRY_DSN": "", "OTEL_EXPORTER_OTLP_ENDPOINT": ""}):
        status = setup_observability()
        assert status["sentry_enabled"] is False
        assert status["opentelemetry_enabled"] is False


def test_setup_observability_with_sentry():
    """Verifica que setup_observability inicialice Sentry cuando SENTRY_DSN está presente."""
    mock_sentry = MagicMock()
    with patch.dict(os.environ, {"SENTRY_DSN": "https://fake_dsn@sentry.io/123"}):
        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            status = setup_observability()
            assert status["sentry_enabled"] is True
            mock_sentry.init.assert_called_once()
