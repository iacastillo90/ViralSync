"""
test_multiplatform_publisher.py

Pruebas unitarias de contrato (TDD) para la Fase 1: Publisher Multi-Plataforma (Instagram, TikTok, YouTube Shorts).
"""

import pytest
import sys
from pathlib import Path

# Añadir el microservicio publisher al path
publisher_dir = str(Path(__file__).parents[2] / "microservices" / "publisher")
if publisher_dir not in sys.path:
    sys.path.insert(0, publisher_dir)

from adapters import PublisherFactory, publish_reel_once, TikTokPublisher, YouTubeShortsPublisher, InstagramGraphPublisher


def test_publisher_factory_instantiates_correct_adapters():
    """REQ-PUB-02: PublisherFactory devuelve la instancia correcta según el nombre de la plataforma."""
    assert isinstance(PublisherFactory.get_publisher("instagram"), InstagramGraphPublisher)
    assert isinstance(PublisherFactory.get_publisher("tiktok"), TikTokPublisher)
    assert isinstance(PublisherFactory.get_publisher("youtube_shorts"), YouTubeShortsPublisher)
    assert isinstance(PublisherFactory.get_publisher("shorts"), YouTubeShortsPublisher)


def test_tiktok_publisher_dev_mode():
    """REQ-PUB-02: TikTokPublisher en entorno dev con token sintético devuelve status=published."""
    publisher = TikTokPublisher()
    res = publish_reel_once(
        publisher,
        idempotency_key="idemp_tiktok_001",
        tenant_id="tenant_tiktok_dev",
        video_url="http://localhost:9000/media/video.mp4",
        caption="Post de prueba TikTok #viral",
        platform="tiktok",
        token="token_tiktok_synth_123",
    )
    assert res["status"] == "published"
    assert res["platform"] == "tiktok"
    assert "tiktok_video_" in res["published_post_id"]


def test_youtube_shorts_publisher_dev_mode():
    """REQ-PUB-02: YouTubeShortsPublisher en entorno dev con token sintético devuelve status=published."""
    publisher = YouTubeShortsPublisher()
    res = publish_reel_once(
        publisher,
        idempotency_key="idemp_yt_001",
        tenant_id="tenant_yt_dev",
        video_url="http://localhost:9000/media/video.mp4",
        caption="Post de prueba YouTube Shorts #shorts",
        platform="youtube_shorts",
        token="token_yt_synth_123",
    )
    assert res["status"] == "published"
    assert res["platform"] == "youtube_shorts"
    assert "yt_short_" in res["published_post_id"]
