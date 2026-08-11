"""
test_rate_limiter.py

Pruebas unitarias para verificar el módulo de Rate Limiting (REQ-RAT-01).
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.security.rate_limiter import check_rate_limit


def test_rate_limiter_allows_under_limit():
    """Verifica que las peticiones por debajo del límite sean permitidas."""
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 5  # Petición 5 de 30
    
    with patch("backend.security.rate_limiter._redis_client", mock_redis):
        allowed = check_rate_limit("tenant_rate_test", limit=30, window_seconds=60)
        assert allowed is True


def test_rate_limiter_blocks_over_limit():
    """Verifica que las peticiones por encima del límite sean rechazadas."""
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 31  # Petición 31 de 30
    
    with patch("backend.security.rate_limiter._redis_client", mock_redis):
        allowed = check_rate_limit("tenant_rate_test", limit=30, window_seconds=60)
        assert allowed is False


def test_rate_limiter_fallback_when_no_redis():
    """Verifica que sin servidor Redis el limitador no bloquee la API (fallback seguro)."""
    with patch("backend.security.rate_limiter._redis_client", None):
        allowed = check_rate_limit("tenant_rate_test", limit=30, window_seconds=60)
        assert allowed is True
