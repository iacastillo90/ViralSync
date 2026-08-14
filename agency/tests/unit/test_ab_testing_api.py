"""
test_ab_testing_api.py

Pruebas unitarias para el router de A/B Testing de Ganchos (Fase 4B).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_create_and_list_variants():
    from backend.routers.ab_testing import create_script_variant, list_script_variants, VariantCreateReq

    mock_db = AsyncMock()

    mock_script = MagicMock()
    mock_script.id = "script_123"
    mock_script.gancho_0_5s = "¿Sabías que el 90% comete este error?"

    mock_variant = MagicMock()
    mock_variant.id = "var_123"
    mock_variant.script_id = "script_123"
    mock_variant.variant_label = "B"
    mock_variant.gancho_0_5s_variant = "Stop de cometer este error hoy mismo."
    mock_variant.views_72h = 0
    mock_variant.conversion_72h = 0
    mock_variant.winner = False
    mock_variant.created_at = None

    mock_script_scalars = MagicMock()
    mock_script_scalars.scalars.return_value.first.return_value = mock_script

    mock_variant_scalars = MagicMock()
    mock_variant_scalars.scalars.return_value.all.return_value = [mock_variant]

    mock_db.execute.side_effect = [
        mock_script_scalars,   # select script for create
        mock_script_scalars,   # select script for list
        mock_variant_scalars,  # select variants for list
    ]

    req = VariantCreateReq(variant_text="Stop de cometer este error hoy mismo.", variant_label="B")
    created = asyncio.run(create_script_variant("tenant_123", "script_123", req, db=mock_db))
    assert created["status"] == "CREATED"
    assert created["variant_label"] == "B"

    listed = asyncio.run(list_script_variants("tenant_123", "script_123", db=mock_db))
    assert len(listed) == 2  # Original A + Variant B
    assert listed[0]["variant_label"] == "A (Original)"
    assert listed[1]["variant_label"] == "Variante B"
