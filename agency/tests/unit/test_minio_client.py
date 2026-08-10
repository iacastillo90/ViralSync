"""
test_minio_client.py

Focused test for RISK-01: the MinIO bucket `viralsync-media` must stay PRIVATE
by default. The anonymous public-read policy (`s3:GetObject` for
`Principal: {"AWS": ["*"]}`) was removed from `MinIOStorageClient.__init__`.
Media access is only exposed through the existing presigned URLs.

These tests verify the client NEVER applies a public bucket policy on bucket
creation (and never calls set_bucket_policy at all).
"""

import backend.storage.minio_client as minio_module
from backend.storage.minio_client import MinIOStorageClient


class FakeMinio:
    """Minio SDK fake that records bucket-related calls."""

    def __init__(self, *args, **kwargs):
        self.calls = []
        self.bucket_exists_result = False

    def bucket_exists(self, bucket):
        return self.bucket_exists_result

    def make_bucket(self, bucket):
        self.calls.append(("make_bucket", bucket))

    def set_bucket_policy(self, bucket, policy):
        self.calls.append(("set_bucket_policy", bucket, policy))


def test_new_bucket_creation_never_applies_public_policy(monkeypatch):
    """RISK-01: when the bucket does not exist it is created, but NO public
    policy is applied — set_bucket_policy must not be called at all."""
    fake = FakeMinio()
    monkeypatch.setattr(minio_module, "Minio", lambda *a, **kw: fake)
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)

    client = MinIOStorageClient()

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


def client_has_no_public_policy(fake):
    return all(call[0] != "set_bucket_policy" for call in fake.calls)