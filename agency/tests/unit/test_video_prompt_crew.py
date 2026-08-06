"""
test_video_prompt_crew.py

Pruebas unitarias para el Agente CrewAI de Prompting Visual y Directiva de Cámara.
"""

from agents.crews.video_prompt_crew import run_video_prompt_crew
from agents.mcp_servers.video_gen_client import generate_storyboard_videos, VideoGenerationClient


def test_video_prompt_crew_storyboard_generation():
    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu SaaS en 2026.",
        "contexto_5_30s": "El error principal es la falta de foco en retención.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta DEMO para darte acceso.",
        "keyword": "DEMO",
    }
    idea = {"texto": "Escalamiento SaaS", "niche": "B2B Software"}

    storyboard = run_video_prompt_crew(script=script, idea=idea)

    assert isinstance(storyboard, list)
    assert len(storyboard) == 4
    
    first_scene = storyboard[0]
    assert first_scene["block_type"] == "gancho"
    assert first_scene["timestamp_range"] == "0s - 5s"
    assert "visual_prompt" in first_scene
    assert "9:16" in first_scene["visual_prompt"]
    assert "camera_shot" in first_scene


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
