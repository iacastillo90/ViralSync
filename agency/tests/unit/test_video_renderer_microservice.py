"""
test_video_renderer_microservice.py

Pruebas unitarias para el microservicio de renderizado faceless (app.py) y el Agente Director (video_director_crew.py).

PR-A / WU1: tests del contrato aditivo scenes[] del renderer (REQ-VSR-01..06).
edge_tts / minio se stubbean en sys.modules (design: "mock edge_tts, requests, moviepy");
el pipeline se mockea por monkeypatch de las funciones de modulo (zero tokens, sin red).
"""

import os
import sys
import types

from agents.crews.video_director_crew import run_video_director_crew, extract_keywords_from_script
from workers.video_edit_task import trigger_video_render

# ---------------------------------------------------------------------------
# Import stubs para el microservicio renderer (edge_tts/minio no instalados en
# el venv de agency; el design pide mockearlos para las pruebas de pipeline).
# ---------------------------------------------------------------------------
_EDGE_TTS_STUB = types.ModuleType("edge_tts")
_MINIO_STUB = types.ModuleType("minio")


class _StubCommunicate:
    def __init__(self, *args, **kwargs):
        pass

    async def save(self, *args, **kwargs):
        pass


class _StubMinio:
    def __init__(self, *args, **kwargs):
        pass


_EDGE_TTS_STUB.Communicate = _StubCommunicate
_MINIO_STUB.Minio = _StubMinio
sys.modules.setdefault("edge_tts", _EDGE_TTS_STUB)
sys.modules.setdefault("minio", _MINIO_STUB)

from fastapi.testclient import TestClient  # noqa: E402

from microservices.renderer import app as renderer_app  # noqa: E402

# `renderer_app` es el MÓDULO (para monkeypatch de sus globales); la instancia
# FastAPI para TestClient es renderer_app.app.
RENDERER_FASTAPI_APP = renderer_app.app  # noqa: E402


def test_video_director_crew_payload_formatting():
    script = {
        "gancho_0_5s": "3 errores fatales al escalar tu software SaaS en 2026.",
        "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco ni automatización. Cuando simplificas tu arquitectura, la conversión aumenta.",
        "moraleja_30_50s": "Primero valida la tracción orgánica y la entrega de valor sin fricción antes de invertir en anuncios.",
        "cta_50_60s": "Comenta SISTEMA abajo.",
        "keyword": "SISTEMA",
    }
    idea = {"texto": "Automatización Empresarial B2B"}

    director_res = run_video_director_crew(script=script, idea=idea, tenant_id="tenant-director-test")

    assert director_res["approved_for_render"] is True
    assert director_res["quality_score"] >= 0.70
    render_payload = director_res["render_payload"]
    assert "Automatización Empresarial B2B" in render_payload["title"]
    assert "3 errores fatales" in render_payload["script_text"]
    assert "Comenta SISTEMA" in render_payload["script_text"]
    assert isinstance(render_payload["keywords"], list)
    assert len(render_payload["keywords"]) > 0
    assert render_payload["tenant_id"] == "tenant-director-test"


def test_extract_keywords_from_script():
    keywords = extract_keywords_from_script("Texto de prueba para automatización de marketing", "Inteligencia Artificial SaaS")
    assert isinstance(keywords, list)
    assert len(keywords) <= 4
    assert "business" in keywords or "inteligencia" in keywords


def test_trigger_video_render_task_fallback():
    """RELIABILITY-001: sin un render real disponible (json2video/local caídos),
    trigger_video_render NUNCA fabrica una URL default — devuelve status 'failed'
    con video_url vacía y un mensaje honesto."""
    good_script = {
        "gancho_0_5s": "3 errores masivos al escalar tu software SaaS en 2026.",
        "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco ni automatización. Cuando simplificas tu arquitectura, la conversión aumenta.",
        "moraleja_30_50s": "Primero valida la tracción orgánica y la entrega de valor sin fricción antes de invertir en anuncios.",
        "cta_50_60s": "Comenta la palabra DEMO abajo y te enviamos el desglose.",
        "keyword": "DEMO",
    }
    result = trigger_video_render.run(tenant_id="tenant-task-test", script=good_script)

    assert result["status"] == "failed"
    assert result["video_url"] == ""  # nunca una URL fabricada
    assert result["message"]
    assert result["tenant_id"] == "tenant-task-test"
    assert "default_rendered_output.mp4" not in str(result)


# ===========================================================================
# PR-A / WU1 — Contrato aditivo scenes[] del renderer (REQ-VSR-01..06)
# ===========================================================================
DEFAULT_VOICE = renderer_app.DEFAULT_VOICE
RENDER_URL = "/render"


def _stub_render_pipeline(monkeypatch):
    """Mockea el pipeline del renderer (edge_tts/Pexels/MoviePy/MinIO/SSE) y
    registra cada llamada real de producción en `calls` para aserciones."""
    calls = {
        "tts": [],
        "search": [],
        "compose_flat": [],
        "compose_scenes": [],
        "upload": [],
        "progress": [],
        "audio_duration": [],
    }

    async def fake_generate_speech_audio(text, output_path, voice=DEFAULT_VOICE):
        calls["tts"].append({"text": text, "output_path": output_path, "voice": voice})
        return output_path

    def fake_download_pexels_videos(keywords, temp_dir, per_page=4):
        calls["search"].append({"keywords": list(keywords), "per_page": per_page})
        return [os.path.join(temp_dir, f"clip_{len(calls['search'])}.mp4")]

    def fake_compose_flat(audio_path, video_paths, output_path):
        calls["compose_flat"].append({"audio_path": audio_path, "n_clips": len(video_paths)})
        return 45.0

    def fake_compose_scenes(segments, output_path, total_duration):
        calls["compose_scenes"].append({"segments": segments, "total_duration": total_duration})
        return total_duration

    def fake_upload(file_path, tenant_id):
        calls["upload"].append({"tenant_id": tenant_id})
        return f"http://minio.local/bucket/{tenant_id}/faceless_output.mp4"

    def fake_progress(tenant_id, stage, message, percent):
        calls["progress"].append({"stage": stage, "percent": percent})

    def fake_audio_duration(audio_path):
        calls["audio_duration"].append(audio_path)
        return 12.0

    monkeypatch.setattr(renderer_app, "generate_speech_audio", fake_generate_speech_audio)
    monkeypatch.setattr(renderer_app, "download_pexels_videos", fake_download_pexels_videos)
    monkeypatch.setattr(renderer_app, "compose_video_moviepy", fake_compose_flat)
    monkeypatch.setattr(renderer_app, "compose_scenes_video_moviepy", fake_compose_scenes, raising=False)
    monkeypatch.setattr(renderer_app, "upload_to_minio", fake_upload)
    monkeypatch.setattr(renderer_app, "report_render_progress", fake_progress)
    monkeypatch.setattr(renderer_app, "audio_duration_seconds", fake_audio_duration, raising=False)
    return calls


def _flat_payload(**overrides):
    payload = {
        "title": "3 Errores al Escalar B2B",
        "script_text": "El error principal es intentar abarcar todo sin foco.",
        "keywords": ["business", "technology", "office"],
        "tenant_id": "tenant-renderer-test",
    }
    payload.update(overrides)
    return payload


# --- VSR-06-1: escenas malformadas → 4xx, sin render de fallback -------------

def test_renderer_scenes_validation_missing_text_422(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    resp = client.post(RENDER_URL, json=_flat_payload(scenes=[{"block": "gancho"}]))

    assert resp.status_code == 422  # 4xx nombrando la escena inválida
    assert "scenes" in resp.text
    assert "text" in resp.text
    assert calls["tts"] == []  # NO renderiza un video de fallback


def test_renderer_scenes_validation_missing_block_422(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    resp = client.post(RENDER_URL, json=_flat_payload(scenes=[{"text": "Hola"}]))
    resp2 = client.post(RENDER_URL, json=_flat_payload(scenes=[{"tts_voice": "es-MX-DaliaNeural", "text": "Hola"}]))

    assert resp.status_code == 422
    assert "block" in resp.text
    assert resp2.status_code == 422
    assert "block" in resp2.text
    assert calls["tts"] == []


def test_renderer_scenes_validation_empty_text_422(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    resp = client.post(RENDER_URL, json=_flat_payload(scenes=[{"block": "gancho", "text": ""}]))

    assert resp.status_code == 422
    assert "text" in resp.text
    assert calls["tts"] == []


def test_renderer_scenes_validation_non_string_text_422(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    resp = client.post(RENDER_URL, json=_flat_payload(scenes=[{"block": "gancho", "text": 12345}]))

    assert resp.status_code == 422
    assert calls["tts"] == []


def test_renderer_scenes_validation_nonpositive_duration_422(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    for bad_duration in (0, -3, -0.1):
        resp = client.post(
            RENDER_URL,
            json=_flat_payload(scenes=[{"block": "gancho", "text": "Hola", "duration_s": bad_duration}]),
        )
        assert resp.status_code == 422
    assert calls["tts"] == []


# --- VSR-06-3: claves desconocidas ignoradas (forward compat) ----------------

def test_renderer_scenes_unknown_keys_ignored(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    scene = {
        "block": "gancho",
        "text": "Texto de la escena",
        "tts_voice": "es-MX-DaliaNeural",
        "visual_prompt": "Oficina moderna",
        "duration_s": 5.0,
        "future_feature_key": "ignored",
        "otra_clave": 123,
    }
    resp = client.post(RENDER_URL, json=_flat_payload(scenes=[scene]))

    assert resp.status_code == 201
    assert len(calls["tts"]) == 1
    assert calls["tts"][0]["text"] == "Texto de la escena"  # render por escena, no flat
    assert calls["tts"][0]["voice"] == "es-MX-DaliaNeural"
    assert calls["search"][0]["per_page"] == 2


# --- VSR-01-1: payload de 4 escenas → render por escena ----------------------

def test_renderer_scenes_4_scene_payload_per_scene_render(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    scenes = [
        {"block": "gancho", "text": "Texto uno", "tts_voice": "es-MX-JorgeNeural"},
        {"block": "contexto", "text": "Texto dos", "visual_prompt": "Oficina moderna con luz"},
        {"block": "moraleja", "text": "Texto tres", "duration_s": 10.0},
        {"block": "cta", "text": "Texto cuatro"},
    ]
    resp = client.post(RENDER_URL, json=_flat_payload(scenes=scenes))

    assert resp.status_code == 201
    # VSR-03: TTS por escena, en orden, voz declarada o DEFAULT_VOICE
    assert len(calls["tts"]) == 4
    assert [c["text"] for c in calls["tts"]] == ["Texto uno", "Texto dos", "Texto tres", "Texto cuatro"]
    assert calls["tts"][0]["voice"] == "es-MX-JorgeNeural"
    assert calls["tts"][1]["voice"] == DEFAULT_VOICE  # VSR-03-2 sin tts_voice
    assert calls["tts"][2]["voice"] == DEFAULT_VOICE
    assert calls["tts"][3]["voice"] == DEFAULT_VOICE
    # VSR-04: b-roll por escena, keywords derivadas de visual_prompt o payload
    assert len(calls["search"]) == 4
    assert [s["per_page"] for s in calls["search"]] == [2, 2, 2, 2]  # D3: búsquedas acotadas
    assert calls["search"][0]["keywords"] == ["business", "technology", "office"]  # VSR-04-2 fallback
    assert calls["search"][1]["keywords"] == ["Oficina", "moderna", "con", "luz"]  # VSR-04-1 prompt
    assert calls["search"][2]["keywords"] == ["business", "technology", "office"]
    assert calls["search"][3]["keywords"] == ["business", "technology", "office"]
    # VSR-05: duración por escena (duration_s o largo TTS 12.0) y cap total
    segments = calls["compose_scenes"][0]["segments"]
    assert [s["duration"] for s in segments] == [12.0, 12.0, 10.0, 12.0]
    assert all(segments[i]["audio_path"].endswith(f"scene_{i}.mp3") for i in range(4))
    assert all(len(s["video_paths"]) == 1 for s in segments)
    # suma = 46 → cap default 45.0 (VSR-05: min(sum, max_duration_seconds or 45.0))
    assert calls["compose_scenes"][0]["total_duration"] == 45.0
    # el pipeline flat NO se usa para escenas (branch separado D2)
    assert calls["compose_flat"] == []


# --- VSR-01-2 / VSR-06-2 / VSR-02-1: contractos flat ---------------------------------

def test_renderer_scenes_absent_scenes_uses_flat(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    resp = client.post(RENDER_URL, json=_flat_payload())

    assert resp.status_code == 201
    assert len(calls["tts"]) == 1
    assert calls["tts"][0]["text"] == "El error principal es intentar abarcar todo sin foco."
    assert calls["tts"][0]["voice"] == DEFAULT_VOICE
    assert calls["search"] == [{"keywords": ["business", "technology", "office"], "per_page": 4}]
    assert len(calls["compose_flat"]) == 1
    assert calls["compose_scenes"] == []


def test_renderer_scenes_empty_list_uses_flat(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    resp = client.post(RENDER_URL, json=_flat_payload(scenes=[]))

    assert resp.status_code == 201
    assert len(calls["tts"]) == 1
    assert len(calls["compose_flat"]) == 1
    assert calls["compose_scenes"] == []


def test_renderer_flat_byte_identity_legacy_payload(monkeypatch):
    """VSR-02-1: payload legacy → mismas llamadas/orden/eventos de progreso que pre-cambio."""
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    resp = client.post(RENDER_URL, json=_flat_payload())

    assert resp.status_code == 201
    assert calls["progress"] == [
        {"stage": "start", "percent": 5},
        {"stage": "audio", "percent": 25},
        {"stage": "broll", "percent": 50},
        {"stage": "moviepy", "percent": 75},
        {"stage": "minio", "percent": 90},
        {"stage": "completed", "percent": 100},
    ]
    assert [c["voice"] for c in calls["tts"]] == [DEFAULT_VOICE]
    assert calls["search"] == [{"keywords": ["business", "technology", "office"], "per_page": 4}]
    assert len(calls["compose_flat"]) == 1
    assert len(calls["upload"]) == 1


# --- VSR-05: cap de duración total -------------------------------------------

def test_renderer_scenes_default_cap_45(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    scenes = [
        {"block": "a", "text": "uno", "duration_s": 30.0},
        {"block": "b", "text": "dos", "duration_s": 30.0},
    ]
    resp = client.post(RENDER_URL, json=_flat_payload(scenes=scenes))

    assert resp.status_code == 201
    assert calls["compose_scenes"][0]["total_duration"] == 45.0  # min(60, 45)
    assert resp.json()["duration_seconds"] == 45.0


def test_renderer_scenes_explicit_max_duration_honored(monkeypatch):
    calls = _stub_render_pipeline(monkeypatch)
    client = TestClient(RENDERER_FASTAPI_APP)

    scenes = [
        {"block": "a", "text": "uno", "duration_s": 30.0},
        {"block": "b", "text": "dos", "duration_s": 30.0},
    ]
    resp = client.post(RENDER_URL, json=_flat_payload(max_duration_seconds=70.0, scenes=scenes))

    assert resp.status_code == 201
    assert calls["compose_scenes"][0]["total_duration"] == 60.0  # 60 <= 70 → sin cap


# --- Helpers puros -----------------------------------------------------------

def test_renderer_keywords_from_prompt():
    assert renderer_app._keywords_from_prompt("Oficina moderna con luz natural", ["business"]) == [
        "Oficina", "moderna", "con", "luz", "natural",
    ]
    assert renderer_app._keywords_from_prompt("", ["business"]) == ["business"]
    assert renderer_app._keywords_from_prompt(None, ["business", "tech"]) == ["business", "tech"]


def test_renderer_total_duration_cap():
    assert renderer_app._scenes_total_duration([10.0, 5.0], 45.0) == 15.0  # bajo el cap → suma
    assert renderer_app._scenes_total_duration([20.0, 20.0, 20.0], 45.0) == 45.0  # sobre → cap
    assert renderer_app._scenes_total_duration([20.0, 20.0, 20.0], None) == 45.0  # None → 45.0
    assert renderer_app._scenes_total_duration([20.0, 20.0, 20.0], 60.0) == 60.0  # cap explícito mayor


def test_renderer_scene_duration_explicit_beats_audio(monkeypatch):
    seen = []

    def spy_audio_duration(audio_path):
        seen.append(audio_path)
        return 999.0

    monkeypatch.setattr(renderer_app, "audio_duration_seconds", spy_audio_duration)
    scene = renderer_app.RenderScene(block="gancho", text="Hola", duration_s=12.0)

    assert renderer_app._scene_duration_seconds(scene, "/tmp/scene_0.mp3") == 12.0
    assert seen == []  # VSR-05-1: duration_s gana, no se lee el audio TTS


def test_renderer_scene_duration_falls_back_to_audio_length(monkeypatch):
    seen = []

    def spy_audio_duration(audio_path):
        seen.append(audio_path)
        return 7.5

    monkeypatch.setattr(renderer_app, "audio_duration_seconds", spy_audio_duration)
    scene = renderer_app.RenderScene(block="gancho", text="Hola")

    assert renderer_app._scene_duration_seconds(scene, "/tmp/scene_0.mp3") == 7.5
    assert seen == ["/tmp/scene_0.mp3"]  # VSR-05-2: duración natural del TTS
