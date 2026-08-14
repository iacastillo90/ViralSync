"""
test_admin_tenants.py

Pruebas unitarias para el endpoint de detalles multi-tenant para administradores (Fase 3C).
"""

import asyncio
from backend.routers.health import get_admin_tenants_details


def test_get_admin_tenants_details():
    res = asyncio.run(get_admin_tenants_details())
    assert isinstance(res, list)
    assert len(res) >= 1
    first = res[0]
    assert "id" in first
    assert "name" in first
    assert "counts" in first
