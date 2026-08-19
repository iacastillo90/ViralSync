"""
test_calendar_api.py

Pruebas unitarias e integración para el router del Calendario Editorial
(/tenants/{tenant_id}/calendar). Verifica la grilla de publicaciones y la
programación de videos (REQ-PUB-06: POST /calendar/schedule persiste la
plataforma elegida además de aprobar el video para el beat diario).
"""

import asyncio
import uuid as uuid_mod
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient

from backend.db.models import Idea, Script, Tenant, Video
from backend.db.session import AsyncSessionLocal, init_db
from backend.main import app

client = TestClient(app)


def run(coro):
    return asyncio.run(coro)


def _seed_video():
    """Crea tenant + idea + script + video aislados por test. Devuelve el video."""
    tenant_id = str(uuid_mod.uuid4())

    async def _run():
        await init_db()
        async with AsyncSessionLocal() as session:
            tenant = Tenant(id=tenant_id, name="Tenant calendar")
            session.add(tenant)
            idea = Idea(
                id=str(uuid_mod.uuid4()),
                tenant_id=tenant_id,
                texto="Idea de calendario",
            )
            session.add(idea)
            await session.flush()
            script = Script(
                id=str(uuid_mod.uuid4()),
                tenant_id=tenant_id,
                idea_id=idea.id,
                gancho_0_5s="Gancho calendario",
                contexto_5_30s="Contexto",
                moraleja_30_50s="Moraleja",
                cta_50_60s="CTA",
            )
            session.add(script)
            await session.flush()
            video = Video(
                id=str(uuid_mod.uuid4()),
                tenant_id=tenant_id,
                script_id=script.id,
                edited_video_uri="s3://bucket/calendario.mp4",
                provider="json2video",
                platform="instagram",
            )
            session.add(video)
            await session.commit()
            return tenant_id, video.id

    return run(_run())


def _load_video_platform(video_id):
    async def _run():
        async with AsyncSessionLocal() as session:
            video = await session.get(Video, video_id)
            return video.platform

    return run(_run())


def test_get_calendar_grid():
    """Verifica que GET /tenants/{tenant_id}/calendar responda 200 con la grilla."""
    tenant_id, _ = _seed_video()
    response = client.get(f"/api/v1/tenants/{tenant_id}/calendar")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["video_id"] is not None
    assert item["edited_video_uri"].endswith(".mp4")
    assert item["publish_approval_status"] == "pending"


def test_schedule_video_publication():
    """REQ-PUB-06: POST /calendar/schedule crea el registro, aprueba el video
    para el beat y PERSISTE la plataforma elegida en videos.platform."""
    tenant_id, target_video_id = _seed_video()
    target_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    payload = {
        "video_id": target_video_id,
        "scheduled_at": target_time,
        "platform": "tiktok",
        "caption": "Reel Comercial Agendado por ViralSync AI",
    }

    res_schedule = client.post(f"/api/v1/tenants/{tenant_id}/calendar/schedule", json=payload)
    assert res_schedule.status_code == 200
    sched_data = res_schedule.json()
    assert sched_data["status"] == "success"
    assert sched_data["video_id"] == target_video_id
    # El endpoint aprueba el video para que el beat diario lo recoga
    assert sched_data["publish_approval_status"] == "approved"
    assert sched_data["platform"] == "tiktok"

    # La plataforma quedó persistida en la columna videos.platform
    assert _load_video_platform(target_video_id) == "tiktok"