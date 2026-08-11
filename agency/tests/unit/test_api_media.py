"""
test_api_media.py

Contract tests for the honest media endpoints (storage-honesty, PR #1):

- GET  /api/v1/tenants/{tenant_id}/media            -> 200, real objects or []
- DELETE /api/v1/tenants/{tenant_id}/media/{media_id:path} -> 200 idempotent | 404

Scenarios covered (spec REQ-SH-01/02):
- SH-01-1: list returns REAL objects from MinIO (FakeMinio) with object_key +
  presigned URL (X-Amz-Signature=)
- SH-01-2: empty tenant -> 200 [] (no demo seeds, no registry)
- SH-02-2: repeated DELETE of an in-prefix key -> 200 both times (S3 delete 204)
- SH-02-3: unknown media_id -> 404, nothing deleted
- SH-02-4: out-of-prefix key refused -> 404 and remove_object NEVER called

Zero-token: AsyncClient + ASGITransport + monkeypatched get_client() wired to a
real MinIOStorageClient (pure config) backed by FakeMinio. No network.
"""

from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport

import backend.storage.minio_client as minio_module
from backend.storage.minio_client import MinIOStorageClient

from backend.main import app

# Tenants en espacio propio de este archivo (f0f0…/a5a5…) — el motor SQLite en
# memoria se comparte para TODA la sesión (StaticPool, conftest.py).
MEDIA_TENANT_ID = "f0f0f0f0-1111-2222-3333-444444444444"
MEDIA_OTHER_TENANT_ID = "a5a5a5a5-5555-6666-7777-888888888888"


class FakeMinio:
    """SDK fake con objetos REALES en el bucket: lista por prefijo y elimina."""

    def __init__(self, *args, **kwargs):
        self.bucket_exists_result = True
        self.objects = {}
        self.list_objects_calls = []
        self.remove_object_calls = []
        self.presigned_calls = []

    def bucket_exists(self, bucket):
        return self.bucket_exists_result

    def make_bucket(self, bucket):
        pass

    def put_object(self, bucket_name, object_name, data, length, content_type=None):
        self.objects[object_name] = {
            "size": length,
            "last_modified": datetime.now(timezone.utc),
        }

    def list_objects(self, bucket_name, prefix=None, recursive=False):
        self.list_objects_calls.append((bucket_name, prefix, recursive))
        return [
            SimpleNamespace(
                object_name=key, size=meta["size"], last_modified=meta["last_modified"]
            )
            for key, meta in self.objects.items()
            if prefix is None or key.startswith(prefix)
        ]

    def remove_object(self, bucket_name, object_name):
        self.remove_object_calls.append((bucket_name, object_name))
        self.objects.pop(object_name, None)  # idempotente (S3 delete 204)

    def presigned_get_object(self, bucket_name, object_name, expires=None):
        self.presigned_calls.append((bucket_name, object_name))
        return (
            f"http://127.0.0.1:9000/{bucket_name}/{object_name}"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=fake&X-Amz-Signature=fake"
        )


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Descarta el singleton cacheado de get_client() para cada test."""
    minio_module._reset_client()
    yield
    minio_module._reset_client()


@pytest.fixture
def media_env(monkeypatch):
    """Cliente REAL (config pura) cableado a FakeMinio y expuesto vía get_client()
    — el router habla con MinIO a través del mismo seam que producción."""
    fake = FakeMinio()
    monkeypatch.setattr(minio_module, "Minio", lambda *a, **kw: fake)
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)
    client = MinIOStorageClient()
    monkeypatch.setattr(minio_module, "get_client", lambda: client)
    return fake


@pytest.mark.anyio
async def test_list_media_empty_returns_empty_list(init_test_db, media_env):
    """SH-01-2: tenant sin uploads → 200 [] (sin seeds demo, sin registry)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{MEDIA_TENANT_ID}/media")

    assert response.status_code == 200
    assert response.json() == []
    # El listado honesto consulta el bucket bajo el prefijo del tenant
    assert media_env.list_objects_calls == [
        ("viralsync-media", f"{MEDIA_TENANT_ID}/", True)
    ]


@pytest.mark.anyio
async def test_list_media_returns_real_objects_with_presigned_url(init_test_db, media_env):
    """SH-01-1: objetos REALES bajo {tenant}/ → un item por objeto con
    object_key + URL presignada; los objetos de otros tenants NO aparecen."""
    media_env.objects[f"{MEDIA_TENANT_ID}/products/foto_1.png"] = {
        "size": 1234,
        "last_modified": datetime.now(timezone.utc),
    }
    media_env.objects[f"{MEDIA_TENANT_ID}/videos/reel.mp4"] = {
        "size": 999999,
        "last_modified": datetime.now(timezone.utc),
    }
    media_env.objects[f"{MEDIA_OTHER_TENANT_ID}/products/other.png"] = {
        "size": 1,
        "last_modified": datetime.now(timezone.utc),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/tenants/{MEDIA_TENANT_ID}/media")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2  # solo objetos del tenant, no del otro
    keys = {i["object_key"] for i in items}
    assert keys == {
        f"{MEDIA_TENANT_ID}/products/foto_1.png",
        f"{MEDIA_TENANT_ID}/videos/reel.mp4",
    }
    for item in items:
        assert item["id"] == item["object_key"]  # media_id == object_key (D-3)
        assert "X-Amz-Signature=" in item["url"]  # URL REAL presignada
        assert item["filename"]
        assert item["type"] in ("image", "video")
        assert item["size_bytes"] > 0
        assert item["created_at"]


@pytest.mark.anyio
async def test_delete_media_unknown_id_returns_404(init_test_db, media_env):
    """SH-02-3: media_id desconocido (fuera del prefijo) → 404, nada borrado."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            f"/api/v1/tenants/{MEDIA_TENANT_ID}/media/unknown-id-123"
        )

    assert response.status_code == 404
    assert media_env.remove_object_calls == []


@pytest.mark.anyio
async def test_delete_media_idempotent_repeat(init_test_db, media_env):
    """SH-02-2: borrar dos veces el mismo object_key del tenant → 200 ambas
    (S3 delete 204 idempotente), remove_object llamado cada vez."""
    key = f"{MEDIA_TENANT_ID}/products/foto_1.png"
    media_env.objects[key] = {
        "size": 100,
        "last_modified": datetime.now(timezone.utc),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        first = await ac.delete(f"/api/v1/tenants/{MEDIA_TENANT_ID}/media/{key}")
        second = await ac.delete(f"/api/v1/tenants/{MEDIA_TENANT_ID}/media/{key}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert media_env.remove_object_calls == [
        ("viralsync-media", key),
        ("viralsync-media", key),
    ]
    assert key not in media_env.objects


@pytest.mark.anyio
async def test_delete_media_out_of_prefix_refused_remove_object_never_called(
    init_test_db, media_env
):
    """SH-02-4: clave de OTRO tenant → guard: 404 y remove_object NUNCA se llama
    (el borrado cross-tenant es imposible)."""
    other_key = f"{MEDIA_OTHER_TENANT_ID}/products/victim.png"
    media_env.objects[other_key] = {
        "size": 50,
        "last_modified": datetime.now(timezone.utc),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            f"/api/v1/tenants/{MEDIA_TENANT_ID}/media/{other_key}"
        )

    assert response.status_code == 404
    assert media_env.remove_object_calls == []
    # El objeto del otro tenant sigue intacto en el bucket
    assert other_key in media_env.objects
