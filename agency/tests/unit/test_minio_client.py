"""
test_minio_client.py

Focused tests for RISK-01 + storage-honesty (REQ-SH-01/02/03, slice 1): the
MinIO bucket `viralsync-media` must stay PRIVATE by default. The anonymous
public-read policy (`s3:GetObject` for `Principal: {"AWS": ["*"]}`) was removed
from `MinIOStorageClient.__init__`. Media access is only exposed through the
existing presigned URLs.

These tests verify the client NEVER applies a public bucket policy on bucket
creation (and never calls set_bucket_policy at all), that the constructor is
PURE CONFIG (D-1: no make_bucket at construction — the bucket is created lazily
via `_ensure_bucket()` on first upload), and the config-honesty guards
(SH-03-1/2/3/4: fail-fast creds in staging/prod, secure derivation, init errors
raise — never silent `minio_client=None`).
"""

import importlib
import pytest

import backend.storage.minio_client as minio_module
from backend.storage.minio_client import MinIOStorageClient


class FakeMinio:
    """Minio SDK fake that records bucket-related calls."""

    def __init__(self, *args, **kwargs):
        self.calls = []
        self.bucket_exists_result = False
        self.put_object_calls = []
        self.presigned_calls = []
        # MinIOStorageClient precarga la región por bucket (SigV4 us-east-1)
        # en `_region_map` durante __init__ (ver minio_client.py).
        self._region_map: dict = {}

    def bucket_exists(self, bucket):
        return self.bucket_exists_result

    def make_bucket(self, bucket):
        self.calls.append(("make_bucket", bucket))

    def set_bucket_policy(self, bucket, policy):
        self.calls.append(("set_bucket_policy", bucket, policy))

    def put_object(self, bucket_name, object_name, data, length, content_type=None):
        self.put_object_calls.append((bucket_name, object_name))

    def presigned_get_object(self, bucket_name, object_name, expires=None):
        self.presigned_calls.append((bucket_name, object_name))
        return f"http://localhost:9000/{bucket_name}/{object_name}?X-Amz-Signature=fake"


def test_new_bucket_creation_never_applies_public_policy(monkeypatch):
    """D-1 / RISK-01: el constructor es CONFIG PURA (sin red) — no crea el
    bucket. make_bucket solo ocurre de forma perezosa en _ensure_bucket() tras
    el primer upload, y NUNCA se aplica una política pública."""
    fake = FakeMinio()
    fake.bucket_exists_result = False
    monkeypatch.setattr(minio_module, "Minio", lambda *a, **kw: fake)
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)

    client = MinIOStorageClient()

    # Constructor puro: sin make_bucket, sin set_bucket_policy, sin red
    assert fake.calls == []

    # Primer upload → _ensure_bucket() crea el bucket PRIVADO (sin política)
    client.upload_product_image(b"bytes", "foto.jpg", tenant_id="t-001")
    assert fake.calls == [("make_bucket", "viralsync-media")]
    assert "set_bucket_policy" not in [call[0] for call in fake.calls]


def test_existing_bucket_untouched_without_public_policy(monkeypatch):
    """RISK-01: an existing bucket is left as-is — no policy call, no make_bucket."""
    fake = FakeMinio()
    fake.bucket_exists_result = True
    monkeypatch.setattr(minio_module, "Minio", lambda *a, **kw: fake)
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)

    MinIOStorageClient()

    assert fake.calls == []
    assert client_has_no_public_policy(fake)


def test_default_creds_fail_fast_in_staging_prod(monkeypatch):
    """SH-03-1: credenciales minioadmin por defecto en staging/prod → el módulo
    NO arranca (raise ValueError en import, espejo de session.py:31-32)."""
    monkeypatch.setenv("AGENCY_ENV", "staging")
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="minioadmin"):
        importlib.reload(minio_module)

    # Restaurar estado limpio del módulo para el resto de la sesión
    monkeypatch.setenv("AGENCY_ENV", "dev")
    importlib.reload(minio_module)


def test_secure_derivation_from_scheme_and_env(monkeypatch):
    """SH-03-2/3: secure = True si el endpoint es https:// o MINIO_SECURE es
    truthy; http plano sin MINIO_SECURE → False."""
    # https scheme → True
    monkeypatch.setattr(minio_module, "MINIO_ENDPOINT", "https://minio.example.com")
    monkeypatch.setattr(minio_module, "MINIO_SECURE", False)
    assert minio_module._derive_secure() is True

    # MINIO_SECURE truthy → True aunque el endpoint sea http
    monkeypatch.setattr(minio_module, "MINIO_ENDPOINT", "http://localhost:9000")
    monkeypatch.setattr(minio_module, "MINIO_SECURE", True)
    assert minio_module._derive_secure() is True

    # http plano sin MINIO_SECURE → False
    monkeypatch.setattr(minio_module, "MINIO_ENDPOINT", "http://localhost:9000")
    monkeypatch.setattr(minio_module, "MINIO_SECURE", False)
    assert minio_module._derive_secure() is False


def test_sdk_missing_raises_not_silent_none(monkeypatch):
    """SH-03-4: sin SDK el constructor LANZA RuntimeError — nunca un
    minio_client=None silencioso que degrade el listado."""
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", False)

    with pytest.raises(RuntimeError, match="SDK"):
        MinIOStorageClient()


def client_has_no_public_policy(fake):
    return all(call[0] != "set_bucket_policy" for call in fake.calls)