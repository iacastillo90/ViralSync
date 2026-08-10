"""
test_video_edit_wiring.py

PR-B / WU2: el worker (trigger_video_render) reenvía el storyboard a
``scenes[]`` del render_payload cuando está presente (VSR-01 worker side) y lo
omite cuando no (flat, VSR-02), mientras los campos curados por el director
(title/description/hashtags/keywords) llegan al POST body del renderer.

Celery eager (conftest) + renderer client mockeado (httpx.Client.post) +
fake_acomplete → zero tokens, sin red. LLM-04-2: el payload curado llega al
renderer.
"""

import json
from unittest.mock import MagicMock, patch

from workers.video_edit_task import trigger_video_render, _storyboard_to_scenes

GOOD_SCRIPT = {
    "gancho_0_5s": "3 errores masivos al escalar tu software SaaS en 2026.",
    "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco ni automatización. Cuando simplificas tu arquitectura, la conversión aumenta.",
    "moraleja_30_50s": "Primero valida la tracción orgánica y la entrega de valor sin fricción antes de invertir en anuncios.",
    "cta_50_60s": "Comenta la palabra DEMO abajo y te enviamos el desglose.",
    "keyword": "DEMO",
}
IDEA = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

STORYBOARD = [
    {
        "scene_index": 1,
        "block_type": "gancho",
        "audio_text": "Gancho real del guion.",
        "visual_prompt": "Close-up dashboard",
    },
    {
        "scene_index": 2,
        "block_type": "contexto",
        "audio_text": "Contexto del problema a resolver.",
        "visual_prompt": "Montage office",
    },
    {
        "scene_index": 3,
        "block_type": "moraleja",
        "audio_text": "La moraleja práctica.",
        "visual_prompt": None,
    },
    {
        "scene_index": 4,
        "block_type": "cta",
        "audio_text": "CTA final del video.",
        "visual_prompt": "Text overlay",
    },
]

LLM_JSON = json.dumps(
    {
        "final_title": "Titulo Curado por LLM Wiring",
        "description": "Descripcion curada que llega al POST body.",
        "hashtags": ["#saas", "#growth"],
        "keywords": ["saas", "automation"],
    },
    ensure_ascii=False,
)


async def fake_acomplete(messages, temperature=0.7, max_tokens=1000, **kwargs):
    return LLM_JSON


def _mock_renderer_201(captured, video_url="http://minio:9000/wired.mp4"):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"video_url": video_url}

    def _capture_post(url, **kwargs):
        captured["payload"] = kwargs.get("json", {})
        return mock_resp

    return _capture_post


def test_trigger_video_render_forwards_scenes_and_curated_fields(monkeypatch):
    """VSR-01 (worker side) + LLM-04-2: storyboard presente → scenes[] en el
    payload POST junto con los campos curados por el director (fake_acomplete)."""
    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        "agents.crews.video_director_crew._tenant_within_llm_budget",
        lambda tenant_id: True,
    )

    captured = {}
    with patch("httpx.Client.post", side_effect=_mock_renderer_201(captured)):
        result = trigger_video_render.run(
            tenant_id="tenant-wiring",
            script=GOOD_SCRIPT,
            idea=IDEA,
            storyboard=STORYBOARD,
        )

    assert result["status"] == "completed"
    payload = captured["payload"]
    assert "scenes" in payload
    assert len(payload["scenes"]) == 4
    assert payload["scenes"][0] == {
        "block": "gancho",
        "text": "Gancho real del guion.",
        "visual_prompt": "Close-up dashboard",
    }
    assert payload["scenes"][3]["block"] == "cta"
    # Campos curados por el director (LLM) llegan al POST body (LLM-04-2)
    assert payload["title"] == "Titulo Curado por LLM Wiring"
    assert "Descripcion curada" in payload["description"]
    assert payload["hashtags"] == ["#saas", "#growth"]
    assert payload["keywords"] == ["saas", "automation"]


def test_trigger_video_render_omits_scenes_when_storyboard_absent(monkeypatch):
    """VSR-02 (worker side): sin storyboard → NO llega 'scenes' → render flat."""
    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        "agents.crews.video_director_crew._tenant_within_llm_budget",
        lambda tenant_id: True,
    )

    captured = {}
    with patch("httpx.Client.post", side_effect=_mock_renderer_201(captured, "http://minio:9000/flat.mp4")):
        result = trigger_video_render.run(
            tenant_id="tenant-flat",
            script=GOOD_SCRIPT,
            idea=IDEA,
        )

    assert result["status"] == "completed"
    payload = captured["payload"]
    assert "scenes" not in payload
    assert payload["script_text"]  # sigue siendo el payload flat clásico


def test_storyboard_to_scenes_mapping_happy_path():
    """Mapeo storyboard → scenes: block/text/visual_prompt de la crew
    video_prompt_crew llegan como RenderScene payloads."""
    scenes = _storyboard_to_scenes(STORYBOARD)

    assert len(scenes) == 4
    assert scenes[0]["block"] == "gancho"
    assert scenes[0]["text"] == "Gancho real del guion."
    assert scenes[0]["visual_prompt"] == "Close-up dashboard"
    # Escena sin visual_prompt: la clave opcional se omite
    assert "visual_prompt" not in scenes[2]


def test_storyboard_to_scenes_drops_blank_text_and_optional_fields():
    """Triangulación: escenas sin texto narrable / no-dict se descartan;
    tts_voice/duration_s opcionales se mapean; None/[] → [] (flat)."""
    sb = [
        {"block_type": "gancho", "audio_text": "   "},
        {
            "block_type": "cta",
            "audio_text": "CTA valido",
            "tts_voice": "es-MX-DaliaNeural",
            "duration_s": 5.0,
        },
        "not-a-dict",
    ]

    scenes = _storyboard_to_scenes(sb)

    assert len(scenes) == 1
    assert scenes[0]["block"] == "cta"
    assert scenes[0]["tts_voice"] == "es-MX-DaliaNeural"
    assert scenes[0]["duration_s"] == 5.0
    assert _storyboard_to_scenes(None) == []
    assert _storyboard_to_scenes([]) == []