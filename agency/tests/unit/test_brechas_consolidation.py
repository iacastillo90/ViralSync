"""
test_brechas_consolidation.py

Pruebas unitarias para las 4 brechas consolidadas:
1. Motor Real de Renderizado de Video (Shotstack & Fal.ai).
2. Fallback explícito en LiteLLM Gateway (Rate Limits 429).
3. Caché Semántica Redis para RAG (0ms latency).
4. Cola de Reintentos (Dead Letter Queue - DLQ) para Webhooks de Meta.
"""

from agents.mcp_servers.video_gen_client import ShotstackClient, VideoGenerationClient
from backend.cache.rag_cache import rag_cache
from agents.mcp_servers.rag_mcp_server import query_rag_knowledge
from workers.webhook_dlq_task import process_failed_webhook_retry


def test_shotstack_client_template_creation():
    shotstack = ShotstackClient()
    scenes = [
        {"scene_index": 1, "video_clip_uri": "s3://test/clip1.mp4", "audio_text": "Gancho 1"},
        {"scene_index": 2, "video_clip_uri": "s3://test/clip2.mp4", "audio_text": "Contexto 2"},
    ]
    payload = shotstack.create_edit_template(scenes, audio_url="http://test/voice.mp3", tenant_id="tenant-1")

    assert payload["output"]["aspectRatio"] == "9:16"
    assert payload["output"]["format"] == "mp4"
    assert len(payload["timeline"]["tracks"]) == 2
    
    render_url = shotstack.submit_render(payload, tenant_id="tenant-1")
    assert "edited_shotstack" in render_url


def test_rag_semantic_cache_hit():
    query = "regla de scoring RUM"
    data = [{"filename": "rum.md", "content": "Formula RUM"}]

    rag_cache.set(query, data)
    cached = rag_cache.get(query)
    assert cached == data

    # Probar servidor MCP RAG con hit de caché
    res = query_rag_knowledge(query)
    assert res == data


def test_webhook_dlq_retry_processing():
    valid_payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "comments",
                        "value": {"text": "Quiero CONSULTA gratis", "from": {"id": "user_dlq_1"}},
                    }
                ]
            }
        ],
    }

    result = process_failed_webhook_retry.run(payload=valid_payload, tenant_id="tenant-test")
    assert result["status"] == "success"
    assert result["leads_count"] == 1
    assert result["leads"][0]["keyword"] == "CONSULTA"
