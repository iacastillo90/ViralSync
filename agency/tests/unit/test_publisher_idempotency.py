"""
test_publisher_idempotency.py

Focused test for RESILIENCE-001: `publish_reel_once` dedupes retries carrying
the same idempotency key — a retry returns the already-published post_id and the
underlying adapter is invoked exactly once per key (no duplicate posting).
"""

from microservices.publisher.adapters import publish_reel_once

# Keep the store clean per test run so counts never leak across tests.
from microservices.publisher import adapters as _adapters_module


class _RecordingPublisher:
    """Fake adapter whose publish_reel records every invocation."""

    def __init__(self):
        self.calls = []

    def publish_reel(self, tenant_id, video_url, caption, user_id=None, token=None):
        self.calls.append((tenant_id, video_url, caption))
        return {
            "status": "published",
            "published_post_id": f"ig_reel_{tenant_id[:8]}_{len(self.calls)}",
            "platform": "instagram",
            "tenant_id": tenant_id,
        }


def test_retry_with_same_idempotency_key_publishes_once():
    _adapters_module._PUBLISHED_BY_KEY.clear()
    publisher = _RecordingPublisher()
    key = "idem-key-0001"

    first = publish_reel_once(
        publisher,
        idempotency_key=key,
        tenant_id="tenant-x",
        video_url="http://minio:9000/v/x/final.mp4",
        caption="caption",
        token="token_dev",
    )
    retry = publish_reel_once(
        publisher,
        idempotency_key=key,
        tenant_id="tenant-x",
        video_url="http://minio:9000/v/x/final.mp4",
        caption="caption",
        token="token_dev",
    )

    assert len(publisher.calls) == 1  # el adapter se llamó UNA sola vez
    assert first["published_post_id"] == retry["published_post_id"]
    assert retry["deduped"] is True
    assert first["deduped"] is False


def test_distinct_keys_publish_separately():
    publisher = _RecordingPublisher()
    _adapters_module._PUBLISHED_BY_KEY.clear()

    a = publish_reel_once(
        publisher,
        idempotency_key="idem-key-a",
        tenant_id="tenant-a",
        video_url="http://minio:9000/v/a.mp4",
        caption="c",
    )
    b = publish_reel_once(
        publisher,
        idempotency_key="idem-key-b",
        tenant_id="tenant-b",
        video_url="http://minio:9000/v/b.mp4",
        caption="c",
    )

    assert len(publisher.calls) == 2
    assert a["published_post_id"] != b["published_post_id"]


def test_no_key_means_always_publishes():
    publisher = _RecordingPublisher()
    _adapters_module._PUBLISHED_BY_KEY.clear()

    first = publish_reel_once(
        publisher,
        idempotency_key=None,
        tenant_id="tenant-c",
        video_url="http://minio:9000/v/c.mp4",
        caption="c",
    )
    second = publish_reel_once(
        publisher,
        idempotency_key=None,
        tenant_id="tenant-c",
        video_url="http://minio:9000/v/c.mp4",
        caption="c",
    )

    assert len(publisher.calls) == 2  # sin key: cada intento publica (legacy)
    assert first["published_post_id"] != second["published_post_id"]