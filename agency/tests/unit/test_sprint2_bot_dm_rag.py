"""
test_sprint2_bot_dm_rag.py

Pruebas unitarias de contrato (TDD) para el Sprint 2: Bot Conversacional DM RAG y Handoff de Ventas.
"""

import pytest
import asyncio
from agents.nodes.dm_response import classify_intent, node_dm_response


def test_classify_intent_purchase_intent():
    """REQ-DM-01: Clasificación de intenciones de compra (purchase_intent)."""
    assert classify_intent("¿Cuál es el precio del servicio?") == "purchase_intent"
    assert classify_intent("Quiero comprar el sistema") == "purchase_intent"


def test_node_dm_response_includes_calendly():
    """REQ-DM-02: Intención de compra inyecta link de agendamiento y activa requires_human=True."""
    async def _test():
        state = {
            "tenant_id": "tenant_123",
            "lead_id": "lead_99",
            "incoming_message": "Quiero comprar la solución",
            "conversation_history": [],
            "rag_context": "",
            "reply_text": "",
            "confidence_score": 0.9,
            "intent": "",
            "requires_human": False,
        }
        res = await node_dm_response(state)
        assert res["intent"] == "purchase_intent"
        assert "calendly" in res["reply_text"].lower()
        assert res["requires_human"] is True

    asyncio.run(_test())
