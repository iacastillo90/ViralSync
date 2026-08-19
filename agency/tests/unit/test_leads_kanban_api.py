"""
test_leads_kanban_api.py

Pruebas unitarias para las etapas Kanban del CRM y respuesta por DM (Feature 3).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_update_lead_stage():
    from backend.routers.leads import update_lead_stage, UpdateLeadStageReq

    mock_db = AsyncMock()
    mock_lead = MagicMock()
    mock_lead.id = "lead_123"
    mock_lead.qualification_status = "nuevo"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_lead
    mock_db.execute.return_value = mock_res

    req = UpdateLeadStageReq(stage="cualificado")
    res = asyncio.run(update_lead_stage("tenant_123", "lead_123", req, db=mock_db))
    assert res["status"] == "updated"
    assert res["stage"] == "cualificado"


def test_reply_lead_dm():
    from backend.routers.leads import reply_lead_dm, ReplyLeadDMReq

    req = ReplyLeadDMReq(message_text="Hola, te envío la auditoría solicitada!")
    res = asyncio.run(reply_lead_dm("tenant_123", "lead_123", req, db=None))
    assert res["status"] == "sent"
    assert res["delivered_via"] == "instagram_graph_api_dm"
