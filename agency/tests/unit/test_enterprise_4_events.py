"""
test_enterprise_4_events.py

Pruebas unitarias de contrato (TDD) para los 4 Nuevos Eventos Enterprise (REQ-EVT-01..04).
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from backend.sse_manager import sse_manager
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload
from backend.security.audit_logger import log_audit_event
from workers.rum_learning_task import run_rum_learning_task


def test_inbound_lead_emits_sse_event():
    """REQ-EVT-01 / EVT-01-1: Procesamiento de webhook emite evento SSE lead_captured."""
    mock_publish = MagicMock()
    payload = {
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "user_ig_123"},
                        "message": {"text": "Quiero la CONSULTA de negocio"},
                    }
                ]
            }
        ]
    }

    with patch.object(sse_manager, "publish_event", mock_publish):
        leads = process_instagram_webhook_payload(payload)
        assert len(leads) > 0
        assert mock_publish.called
        event_type = mock_publish.call_args[0][1]
        assert event_type == "lead_captured"


def test_rum_learning_emits_sse_event():
    """REQ-EVT-02 / EVT-02-1: run_rum_learning_task emite evento SSE rum_metrics_evaluated."""
    mock_publish = MagicMock()
    with patch.object(sse_manager, "publish_event", mock_publish):
        res = run_rum_learning_task("tenant_test")
        assert res["status"] == "completed"
        assert mock_publish.called
        event_type = mock_publish.call_args[0][1]
        assert event_type == "rum_metrics_evaluated"


def test_audit_logger_emits_sse_event():
    """REQ-EVT-03 / EVT-03-1: log_audit_event publica evento SSE audit_event_logged."""
    mock_publish = MagicMock()
    with patch.object(sse_manager, "publish_event", mock_publish):
        log_audit_event("tenant_123", "user_1", "idea_approved_by_human", {"idea_id": "uuid-123"})
        assert mock_publish.called
        event_type = mock_publish.call_args[0][1]
        assert event_type == "audit_event_logged"
