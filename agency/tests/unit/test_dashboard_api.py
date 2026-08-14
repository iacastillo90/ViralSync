"""
test_dashboard_api.py

Pruebas unitarias para el router del Dashboard Principal (Fase 2A).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_get_tenant_dashboard():
    from backend.routers.dashboard import get_tenant_dashboard

    mock_db = AsyncMock()

    # Mock para las consultas func.count y func.avg
    mock_scalar_res = MagicMock()
    mock_scalar_res.scalar.side_effect = [5, 10, 3, 2, 88.5]

    # Mock para recent_activity
    mock_scalars = MagicMock()
    mock_script = MagicMock()
    mock_script.id = "script_123"
    mock_script.gancho_0_5s = "¿Sabías este truco?"
    mock_script.approval_status = "approved"
    mock_script.trend_score = 88.5
    mock_script.created_at = None
    mock_scalars.scalars.return_value.all.return_value = [mock_script]
    mock_scalars.scalars.return_value.first.return_value = mock_script

    mock_db.execute.side_effect = [
        mock_scalar_res,  # ideas count
        mock_scalar_res,  # scripts count
        mock_scalar_res,  # videos count
        mock_scalar_res,  # leads count
        mock_scalar_res,  # avg viral score
        mock_scalars,     # latest script
        mock_scalars,     # recent activity
    ]

    res = asyncio.run(get_tenant_dashboard(tenant_id="tenant_abc", db=mock_db))
    assert res["tenant_id"] == "tenant_abc"
    assert "kpis" in res
    assert "pipeline" in res
    assert "recent_activity" in res
