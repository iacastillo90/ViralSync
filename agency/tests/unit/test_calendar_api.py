"""
test_calendar_api.py

Pruebas unitarias e integración para el router del Calendario Editorial (/tenants/{tenant_id}/calendar).
Verifica la obtención de la grilla de publicaciones y la programación asíncrona de videos.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)
TENANT_ID = "92c96882-9eb6-4f50-b7b6-316c3eb6e9a5"


def test_get_calendar_grid():
    """Verifica que el endpoint GET /tenants/{tenant_id}/calendar responda 200 con la grilla."""
    response = client.get(f"/api/v1/tenants/{TENANT_ID}/calendar")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "video_id" in item
        assert "edited_video_uri" in item
        assert "publish_approval_status" in item


def test_schedule_video_publication():
    """Verifica que se pueda agendar la fecha de publicación de un video existente."""
    # 1. Obtener un video existente del tenant
    res_grid = client.get(f"/api/v1/tenants/{TENANT_ID}/calendar")
    grid = res_grid.json()

    if len(grid) > 0:
        target_video_id = grid[0]["video_id"]
        target_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

        payload = {
            "video_id": target_video_id,
            "scheduled_at": target_time,
            "platform": "instagram_reels",
            "caption": "Reel Comercial Agendado por ViralSync AI"
        }

        res_schedule = client.post(f"/api/v1/tenants/{TENANT_ID}/calendar/schedule", json=payload)
        assert res_schedule.status_code == 200
        sched_data = res_schedule.json()
        assert sched_data["status"] == "success"
        assert sched_data["video_id"] == target_video_id
        assert sched_data["publish_approval_status"] == "scheduled"
