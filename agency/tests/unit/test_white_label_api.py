"""
test_white_label_api.py

Pruebas unitarias para la personalización de Marca Blanca (Feature 4).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock


def test_get_and_update_tenant_branding():
    from backend.routers.branding import get_tenant_branding, update_tenant_branding, UpdateBrandingReq

    mock_db = AsyncMock()
    mock_tenant = MagicMock()
    mock_tenant.id = "tenant_123"
    mock_tenant.name = "Agencia Demo"

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_tenant
    mock_db.execute.return_value = mock_res

    branding = asyncio.run(get_tenant_branding("tenant_123", db=mock_db))
    assert branding["tenant_id"] == "tenant_123"

    req = UpdateBrandingReq(agency_name="Agencia Elite 360", primary_color="#10B981")
    updated = asyncio.run(update_tenant_branding("tenant_123", req, db=mock_db))
    assert updated["status"] == "success"
    assert updated["agency_name"] == "Agencia Elite 360"
    assert updated["primary_color"] == "#10B981"
