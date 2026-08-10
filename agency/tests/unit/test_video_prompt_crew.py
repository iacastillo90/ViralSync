"""
test_video_prompt_crew.py

Pruebas unitarias para el Agente CrewAI de Prompting Visual y Directiva de Cámara.
"""

import asyncio
import json

from agents.crews import video_prompt_crew
from agents.crews.video_prompt_crew import run_video_prompt_crew
from agents.mcp_servers.video_gen_client import generate_storyboard_videos, VideoGenerationClient

LLM_STORYBOARD = json.dumps([
    {
        "scene_index": i,
        "timestamp_range": f"{i * 5}s - {(i + 1) * 5}s",
        "block_type": "gancho",
        "audio_text": "audio",
        "camera_shot": "Macro Close-Up",
        "visual_mode": "TEXT_TO_VIDEO",
        "visual_prompt": "9:16 vertical cinematic prompt for the scene",
    }
    for i in range(1, 5)
])


def test_video_prompt_crew_storyboard_generation():
    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu SaaS en 2026.",
        "contexto_5_30s": "El error principal es la falta de foco en retención.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta DEMO para darte acceso.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    storyboard = asyncio.run(run_video_prompt_crew(script=script, idea=idea))

    assert isinstance(storyboard, list)
    assert len(storyboard) == 4
    
    first_scene = storyboard[0]
    assert first_scene["block_type"] == "gancho"
    assert first_scene["timestamp_range"] == "0s - 5s"
    assert "visual_prompt" in first_scene
    assert "9:16" in first_scene["visual_prompt"]
    assert "camera_shot" in first_scene


def test_video_prompt_crew_injects_rum_threshold_and_trends(monkeypatch):
    # CVD-03-1 + CVD-04-1: prompt seam carries the Redis RUM threshold (0.78)
    # and the sanitized trend section when both are present.
    calls = {}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=1500, **kwargs):
        calls["user_prompt"] = messages[1]["content"]
        return LLM_STORYBOARD

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        video_prompt_crew, "resolve_rum_threshold", lambda niche: 0.78
    )
    monkeypatch.setattr(
        video_prompt_crew, "build_trend_section", lambda niche: "- Reels virales SaaS 2026"
    )

    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu SaaS en 2026.",
        "contexto_5_30s": "El error principal es la falta de foco en retención.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta DEMO para darte acceso.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    storyboard = asyncio.run(run_video_prompt_crew(script=script, idea=idea))

    assert len(storyboard) == 4  # LLM path ran -> seam executed
    assert "0.78" in calls["user_prompt"]  # CVD-03-1
    assert "Reels virales SaaS 2026" in calls["user_prompt"]  # CVD-04-1


def test_video_prompt_crew_absent_context_non_fatal(monkeypatch):
    # CVD-03-2 + CVD-04-2: Redis down / cache miss -> clamp default injected,
    # trend section omitted, crew still produces its storyboard.
    calls = {}

    async def fake_acomplete(messages, temperature=0.7, max_tokens=1500, **kwargs):
        calls["user_prompt"] = messages[1]["content"]
        return LLM_STORYBOARD

    monkeypatch.setattr("agents.llm.acomplete", fake_acomplete)
    monkeypatch.setattr(
        video_prompt_crew, "resolve_rum_threshold", lambda niche: 0.70
    )
    monkeypatch.setattr(video_prompt_crew, "build_trend_section", lambda niche: "")

    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu SaaS en 2026.",
        "contexto_5_30s": "El error principal es la falta de foco en retención.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta DEMO para darte acceso.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    storyboard = asyncio.run(run_video_prompt_crew(script=script, idea=idea))

    assert len(storyboard) == 4  # crew still outputs
    assert "0.70" in calls["user_prompt"]  # CVD-03-2 clamp default injected
    assert "Trending topics" not in calls["user_prompt"]  # CVD-04-2 omitted


def test_video_gen_client_mock_provider():
    client = VideoGenerationClient(provider="mock")
    scene = {
        "scene_index": 1,
        "visual_prompt": "9:16 vertical video of modern futuristic office",
    }
    uri = client.generate_scene_video(scene, tenant_id="tenant-test")
    assert "mock_clip_scene_1.mp4" in uri


def test_generate_storyboard_videos():
    storyboard = [
        {"scene_index": 1, "visual_prompt": "Cinematic shot"},
        {"scene_index": 2, "visual_prompt": "Office shot"},
    ]
    result = generate_storyboard_videos(storyboard, tenant_id="tenant-demo")
    assert len(result) == 2
    assert "video_clip_uri" in result[0]
