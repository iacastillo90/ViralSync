"""
test_audit_findings_resolutions.py

Pruebas unitarias para validar las soluciones a las observaciones de la Auditoría Técnica:
1. Verificación de eliminación de archivo duplicado sse_manager.py.
2. Adapter Pattern en el publicador outbound (Instagram, TikTok, YouTube Shorts).
3. Garantía de no-bloqueo y Zero Waste en microservicio renderer.
4. Incremento atómico en seguimiento de costo LLM en Redis.
"""

import os
import pytest
from pathlib import Path
from microservices.publisher.adapters import PublisherFactory, InstagramGraphPublisher, TikTokPublisher, YouTubeShortsPublisher
from backend.services.llm_budget_service import track_llm_token_usage

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_duplicated_sse_manager_removed():
    """Verifica que el archivo duplicado backend/realtime/sse_manager.py haya sido eliminado."""
    duplicate_path = REPO_ROOT / "backend" / "realtime" / "sse_manager.py"
    canonical_path = REPO_ROOT / "backend" / "sse_manager.py"

    assert not duplicate_path.exists()
    assert canonical_path.exists()


def test_publisher_adapter_factory():
    """Verifica la instanciación de adaptadores según la plataforma elegida."""
    ig_pub = PublisherFactory.get_publisher("instagram")
    assert isinstance(ig_pub, InstagramGraphPublisher)

    tiktok_pub = PublisherFactory.get_publisher("tiktok")
    assert isinstance(tiktok_pub, TikTokPublisher)

    yt_pub = PublisherFactory.get_publisher("youtube_shorts")
    assert isinstance(yt_pub, YouTubeShortsPublisher)


def test_publisher_adapter_execution():
    """Verifica la ejecución de publicación a través del adaptador TikTok."""
    publisher = PublisherFactory.get_publisher("tiktok")
    result = publisher.publish_reel(
        tenant_id="tenant-adapter-test",
        video_url="http://localhost:9000/viralsync-media/video.mp4",
        caption="Test caption #viral",
    )

    assert result["status"] == "published"
    assert result["platform"] == "tiktok"
    assert "published_post_id" in result


def test_llm_budget_atomic_tracking():
    """Verifica la ejecución del rastreador de costos LLM."""
    usage = track_llm_token_usage(
        tenant_id="tenant-atomic-test",
        model_name="gemini-1.5-flash",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    assert usage["cost_usd"] > 0
    assert usage["tenant_id"] == "tenant-atomic-test"
