"""
test_sprint3_cicd_rate_limiting.py

Pruebas unitarias de contrato (TDD) para el Sprint 3: Hardening CI/CD y Rate Limiting por Tier.
"""

from backend.security.rate_limiter import get_tenant_tier_rate_limit, check_rate_limit


def test_get_tenant_tier_rate_limit_values():
    """REQ-RAT-01: Verificación de cuotas por tier (free=60, pro=300, enterprise=1000)."""
    assert get_tenant_tier_rate_limit("free") == 60
    assert get_tenant_tier_rate_limit("pro") == 300
    assert get_tenant_tier_rate_limit("enterprise") == 1000
    assert get_tenant_tier_rate_limit("unknown") == 60


def test_check_rate_limit_allowed_fallback():
    """Garantiza degradación suave si no hay Redis en entornos dev/test."""
    allowed = check_rate_limit("tenant_test_123", limit=10)
    assert allowed is True
