"""
test_redis_cache.py

Pruebas unitarias para el servicio de caché Redis (Fase 1B).
"""

from backend.services.redis_cache import cache_set, cache_get, hash_key


def test_hash_key():
    k = hash_key("searxng", " Tendencias Virales Reels ")
    assert k.startswith("searxng:")
    assert len(k) > 10


def test_cache_set_and_get_in_memory_fallback():
    key = "test_key_123"
    data = [{"title": "Test Title", "url": "https://example.com"}]

    assert cache_set(key, data, ttl_seconds=60) is True
    retrieved = cache_get(key)
    assert retrieved == data
