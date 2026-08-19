"""
test_json2video.py

Pruebas unitarias para la integración del cliente de JSON2Video y la tarea de Celery
con tolerancia a fallos y fallback al microservicio local.
"""

import os
from unittest.mock import patch, MagicMock
from agents.mcp_servers.json2video_client import JSON2VideoClient
from workers.video_edit_task import trigger_video_render


def test_json2video_client_pexels_fetching_mock():
    """Valida que _fetch_pexels_video_urls parsee correctamente la respuesta de Pexels API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "videos": [
            {
                "video_files": [
                    {"height": 1080, "link": "https://pexels.com/download/clip_1080p.mp4"},
                    {"height": 360, "link": "https://pexels.com/download/clip_360p.mp4"}
                ]
            }
        ]
    }

    client = JSON2VideoClient(api_key="mock_key")
    client.pexels_api_key = "pexels_mock_key"

    with patch("httpx.Client.get", return_value=mock_resp):
        urls = client._fetch_pexels_video_urls(["business", "marketing"])
        assert len(urls) == 1
        assert urls[0] == "https://pexels.com/download/clip_1080p.mp4"


def test_json2video_client_rendering_and_polling_mock():
    """Valida la creación y el polling exitoso de un proyecto de video en JSON2Video."""
    client = JSON2VideoClient(api_key="mock_key")

    # Mocks para Pexels, POST de creación y GET de polling
    mock_pexels_resp = MagicMock()
    mock_pexels_resp.status_code = 200
    mock_pexels_resp.json.return_value = {
        "videos": [{"video_files": [{"height": 720, "link": "https://pexels.com/clip.mp4"}]}]
    }

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "success": True,
        "project": "proj_998122"
    }

    mock_poll_resp = MagicMock()
    mock_poll_resp.status_code = 200
    mock_poll_resp.json.return_value = {
        "success": True,
        "movie": {
            "status": "done",
            "url": "https://assets.json2video.com/renders/proj_998122.mp4"
        }
    }

    def mock_http_calls(url, *args, **kwargs):
        if "pexels.com" in str(url):
            return mock_pexels_resp
        elif "project=" in str(url):
            return mock_poll_resp
        else:
            return mock_post_resp

    script = {
        "gancho_0_5s": "3 consejos rápidos de productividad.",
        "contexto_5_30s": "Sistematiza tus flujos diarios.",
        "moraleja_30_50s": "El tiempo es tu recurso más escaso.",
        "cta_50_60s": "Síguenos para más.",
    }

    with patch("httpx.Client.get", side_effect=mock_http_calls), \
         patch("httpx.Client.post", side_effect=mock_http_calls), \
         patch("time.sleep", return_value=None):  # Acelerar polling

        video_url = client.render_video(
            script=script,
            keywords=["automation"],
            tenant_id="tenant-test"
        )

        assert video_url == "https://assets.json2video.com/renders/proj_998122.mp4"


@patch.dict(os.environ, {
    "VIDEO_RENDERER_PROVIDER": "json2video",
    "JSON2VIDEO_API_KEY": "valid_mock_key"
})
def test_trigger_video_render_json2video_success():
    """Prueba que trigger_video_render use el cliente JSON2Video si está configurado en el entorno."""
    good_script = {
        "gancho_0_5s": "3 errores masivos al escalar tu software SaaS en 2026.",
        "contexto_5_30s": "El problema principal es intentar abarcar todo sin foco.",
        "moraleja_30_50s": "Primero valida la tracción orgánica.",
        "cta_50_60s": "Comenta la palabra DEMO abajo.",
        "keyword": "DEMO",
    }

    # Mockear el cliente para evitar peticiones de red reales
    mock_render = MagicMock(return_value="https://assets.json2video.com/renders/project_ok.mp4")

    with patch("agents.mcp_servers.json2video_client.JSON2VideoClient.render_video", mock_render), \
         patch("workers.video_edit_task.run_video_director_crew") as mock_director:

        mock_director.return_value = {
            "approved_for_render": True,
            "quality_score": 0.9,
            "quality_feedback": "Perfecto",
            "render_payload": {
                "title": "Escalar SaaS",
                "script_text": "guion completo",
                "keywords": ["saas", "business"],
                "tenant_id": "tenant-json2video-test"
            }
        }

        result = trigger_video_render.run(tenant_id="tenant-json2video-test", script=good_script)

        assert result["status"] == "completed"
        assert result["provider"] == "json2video"
        assert result["video_url"] == "https://assets.json2video.com/renders/project_ok.mp4"


def _captured_render(voice=None):
    """Ejecuta render_video con mocks de red y devuelve el payload POST capturado."""
    client = JSON2VideoClient(api_key="mock_key")
    captured = {}

    def mock_http_calls(url, *args, **kwargs):
        if "pexels.com" in str(url):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"videos": []}
            return resp
        if "project=" in str(url):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "success": True,
                "movie": {"status": "done", "url": "https://cdn.example.com/video.mp4"},
            }
            return resp
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"success": True, "project": "proj_voice_test"}
        captured["payload"] = kwargs.get("json")
        return resp

    script = {
        "gancho_0_5s": "3 consejos rápidos de productividad.",
        "contexto_5_30s": "Sistematiza tus flujos diarios.",
        "moraleja_30_50s": "El tiempo es tu recurso más escaso.",
        "cta_50_60s": "Síguenos para más.",
    }

    with patch("httpx.Client.get", side_effect=mock_http_calls), \
         patch("httpx.Client.post", side_effect=mock_http_calls), \
         patch("time.sleep", return_value=None):
        video_url = client.render_video(
            script=script,
            keywords=["automation"],
            tenant_id="tenant-voice-test",
            title="Voz Parametrizada",
            **({"voice": voice} if voice else {}),
        )
    assert video_url == "https://cdn.example.com/video.mp4"
    assert "payload" in captured, "El payload POST debe haberse capturado"
    return captured["payload"]


def _voice_elements(payload):
    """Extrae los elementos {type: 'voice', model: 'azure'} del payload de escenas."""
    scenes = payload.get("scenes") or []
    return [
        elem
        for scene in scenes
        for elem in (scene.get("elements") or [])
        if elem.get("type") == "voice" and elem.get("model") == "azure"
    ]


def test_render_video_uses_parameterized_voice():
    """REQ-VOICE-03: render_video(..., voice="X") usa `voice: "X"` en todos los
    elementos voice del payload, en lugar del es-MX-JorgeNeural hardcodeado."""
    payload = _captured_render(voice="es-ES-AlvaroNeural")
    voices = _voice_elements(payload)
    assert voices, "El payload debe contener elementos voice (azure)"
    for elem in voices:
        assert elem["voice"] == "es-ES-AlvaroNeural", (
            f"El payload debe usar la voz parametrizada, recibió {elem['voice']}"
        )


def test_render_video_defaults_to_es_mx_jorge_voice():
    """REQ-VOICE-03: sin voice explícito, el payload conserva el default
    es-MX-JorgeNeural (compatibilidad con el comportamiento previo)."""
    payload = _captured_render()
    voices = _voice_elements(payload)
    assert voices, "El payload debe contener elementos voice (azure)"
    for elem in voices:
        assert elem["voice"] == "es-MX-JorgeNeural"


@patch.dict(os.environ, {
    "VIDEO_RENDERER_PROVIDER": "json2video",
    "JSON2VIDEO_API_KEY": "valid_mock_key"
})
def test_trigger_video_render_json2video_fallback_to_local():
    """Prueba que si JSON2Video falla, se realice el fallback automático al microservicio local."""
    good_script = {
        "gancho_0_5s": "3 errores masivos al escalar tu software SaaS.",
        "contexto_5_30s": "Simplifica tu arquitectura.",
        "moraleja_30_50s": "Primero valida.",
        "cta_50_60s": "Comenta abajo.",
        "keyword": "DEMO",
    }

    # Provocar un error en el cliente de JSON2Video
    mock_render = MagicMock(side_effect=RuntimeError("API Error"))

    # Simular una respuesta exitosa del microservicio local
    mock_local_resp = MagicMock()
    mock_local_resp.status_code = 201
    mock_local_resp.json.return_value = {"video_url": "http://minio:9000/local_output.mp4"}

    with patch("agents.mcp_servers.json2video_client.JSON2VideoClient.render_video", mock_render), \
         patch("workers.video_edit_task.run_video_director_crew") as mock_director, \
         patch("httpx.Client.post", return_value=mock_local_resp):

        mock_director.return_value = {
            "approved_for_render": True,
            "quality_score": 0.85,
            "render_payload": {
                "title": "Fallback",
                "script_text": "guion",
                "keywords": ["test"],
                "tenant_id": "tenant-fallback-test"
            }
        }

        result = trigger_video_render.run(tenant_id="tenant-fallback-test", script=good_script)

        # Debería completarse usando el proveedor local como fallback
        assert result["status"] == "completed"
        assert result["provider"] == "local"
        assert result["video_url"] == "http://minio:9000/local_output.mp4"
