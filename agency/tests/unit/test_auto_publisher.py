"""
test_auto_publisher.py

Pruebas unitarias para el worker de auto-publicación multi-canal (publisher_task.py)
y el render de voz por persona (S2b — video_edit_task, REQ-VOICE-02/05).
"""

import asyncio
from unittest.mock import patch, MagicMock
from backend.db.session import init_db
from workers.publisher_task import _publish_to_instagram_reels, auto_publish_scheduled_videos_task
from workers.video_edit_task import trigger_video_render


def test_publish_to_instagram_reels_mock():
    """Verifica que el flujo de publicación devuelva éxito simulado en entorno de prueba."""
    res = asyncio.run(_publish_to_instagram_reels(
        video_url="http://localhost:9000/viralsync-media/test.mp4",
        caption="Reel Test Caption"
    ))
    assert res["status"] == "success"
    assert "post_id" in res


def test_auto_publish_scheduled_videos_task_execution():
    """Verifica la ejecución síncrona de la tarea Celery de auto-publicación."""
    asyncio.run(init_db())
    res = auto_publish_scheduled_videos_task()
    assert res["status"] == "COMPLETED"
    assert "published_count" in res


# ---------------------------------------------------------------------------
# T-S2b-01 — Render inyecta la voz de la persona en cada escena (REQ-VOICE-02/05)
# ---------------------------------------------------------------------------

def _seed_voice_persona(name, edge_voice, azure_voice, locale_voices):
    """Inserta una persona en la DB de test SQLite compartida (idempotente por
    name UNIQUE, mismo patrón que el seed de la migración 012)."""
    import uuid as uuid_mod
    from sqlalchemy import select
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import VoicePersona

    async def _run():
        async with AsyncSessionLocal() as session:
            existing = (
                await session.execute(select(VoicePersona).where(VoicePersona.name == name))
            ).scalars().first()
            if existing:
                return existing
            persona = VoicePersona(
                id=str(uuid_mod.uuid4()),
                name=name,
                description=f"Persona {name}",
                edge_tts_voice=edge_voice,
                json2video_voice=azure_voice,
                locale_voices=locale_voices,
                is_active=True,
            )
            session.add(persona)
            await session.commit()
            return persona

    return asyncio.run(_run())


def _render_script_with_persona(script, persona_id=None):
    """Ejecuta trigger_video_render con storyboard de 2 escenas y director
    mockeado (approved); provider local forzado por conftest. Devuelve el
    resultado completo del worker."""
    from backend.db.session import init_db as _init_db
    asyncio.run(_init_db())

    if persona_id:
        script = {**script, "voice_persona_id": persona_id}

    storyboard = [
        {"scene_index": 1, "block_type": "gancho", "audio_text": "Gancho de prueba"},
        {"scene_index": 2, "block_type": "cta", "audio_text": "CTA de prueba"},
    ]

    mock_director = MagicMock(return_value={
        "approved_for_render": True,
        "quality_score": 0.9,
        "quality_feedback": "OK",
        "render_payload": {"title": "Render Voz", "keywords": ["test"]},
    })
    mock_local_resp = MagicMock()
    mock_local_resp.status_code = 201
    mock_local_resp.json.return_value = {"video_url": "http://minio:9000/local_voz_test.mp4"}

    with patch("workers.video_edit_task.run_video_director_crew", mock_director), \
         patch("httpx.Client.post", return_value=mock_local_resp):
        return trigger_video_render.run(
            tenant_id="tenant-voice-render",
            script=script,
            storyboard=storyboard,
        )


def test_video_edit_injects_persona_voice_into_scenes():
    """REQ-VOICE-02: las escenas del render llevan la voz de la persona asignada
    al guion, NO el es-MX-JorgeNeural por default."""
    persona = _seed_voice_persona(
        "Femenina Corporativa",
        edge_voice="es-MX-DaliaNeural",
        azure_voice="es-MX-DaliaNeural",
        locale_voices={"es": "es-MX-DaliaNeural", "en": "en-US-JennyNeural"},
    )
    script = {"keyword": "SOLICITUD", "gancho_0_5s": "Gancho", "cta_50_60s": "CTA"}

    result = _render_script_with_persona(script, persona_id=persona.id)

    assert result["status"] == "completed", f"Render debe completarse: {result}"
    scenes = (result.get("payload") or {}).get("scenes") or []
    assert len(scenes) == 2, f"Debe haber 2 escenas, recibió {len(scenes)}"
    for scene in scenes:
        assert scene.get("tts_voice") == "es-MX-DaliaNeural", (
            f"Cada escena debe llevar la voz de la persona, recibió {scene.get('tts_voice')}"
        )


def test_video_edit_lang_en_uses_english_voice():
    """REQ-VOICE-05: guion traducido (keyword=LANG:EN) con persona → escenas con
    la voz en inglés de la persona, no la voz nativa."""
    persona = _seed_voice_persona(
        "Masculina Enérgica",
        edge_voice="es-MX-JorgeNeural",
        azure_voice="es-MX-JorgeNeural",
        locale_voices={"es": "es-MX-JorgeNeural", "en": "en-US-ChristopherNeural"},
    )
    script = {"keyword": "LANG:EN", "gancho_0_5s": "Hook", "cta_50_60s": "CTA"}

    result = _render_script_with_persona(script, persona_id=persona.id)

    assert result["status"] == "completed", f"Render debe completarse: {result}"
    scenes = (result.get("payload") or {}).get("scenes") or []
    assert len(scenes) == 2, f"Debe haber 2 escenas, recibió {len(scenes)}"
    for scene in scenes:
        assert scene.get("tts_voice") == "en-US-ChristopherNeural", (
            f"LANG:EN debe resolver la voz en inglés de la persona, recibió {scene.get('tts_voice')}"
        )


def test_video_edit_without_persona_keeps_no_tts_voice():
    """Approval: guion sin persona → las escenas NO llevan tts_voice (el
    renderer cae al DEFAULT_VOICE), comportamiento previo intacto."""
    script = {"keyword": "SOLICITUD", "gancho_0_5s": "Gancho", "cta_50_60s": "CTA"}

    result = _render_script_with_persona(script)

    assert result["status"] == "completed", f"Render debe completarse: {result}"
    scenes = (result.get("payload") or {}).get("scenes") or []
    assert len(scenes) == 2, f"Debe haber 2 escenas, recibió {len(scenes)}"
    for scene in scenes:
        assert "tts_voice" not in scene, "Sin persona, las escenas no deben inyectar tts_voice"
