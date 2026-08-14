"""
test_lead_automation.py

Pruebas unitarias para la captura automática de leads por comentario y envío de DMs (instagram_inbound.py).
"""

import pytest
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload


def test_process_instagram_comment_keyword_audio():
    """Verifica que el comentario con la palabra clave AUDIO genere un lead calificado con auto-respuesta."""
    mock_webhook_payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "entry_123",
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comment_999",
                            "text": "¡Me encanta este micrófono! Quiero más AUDIO por favor",
                            "from": {"id": "user_ig_777", "username": "creador_podcast"}
                        }
                    }
                ]
            }
        ]
    }

    leads = process_instagram_webhook_payload(mock_webhook_payload)
    assert len(leads) == 1
    lead = leads[0]
    assert lead["keyword"] == "AUDIO"
    assert lead["ig_user_id"] == "user_ig_777"
    assert lead["auto_reply_sent"] is True
    assert "https://viralsync.io/oferta/audio" in lead["offer_url"]


def test_process_instagram_comment_no_keyword():
    """Verifica que un comentario común sin palabra clave no genere un lead ambiguo."""
    mock_payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "text": "Excelente video bro, sigue así!",
                            "from": {"id": "user_ig_888"}
                        }
                    }
                ]
            }
        ]
    }
    leads = process_instagram_webhook_payload(mock_payload)
    assert len(leads) == 0
