"""
test_minio_real.py

Real MinIO upload tests for WU-04 (design D6, T-00 verdict #2, REQ-PERSIST-05):
`backend/storage/minio_client.py` must upload through the `minio` SDK and return
a REAL presigned URL (bucket PRIVADO por default) — commiteando SOLO tras éxito
genuino:

- `test_upload_product_image_calls_put_object_and_returns_presigned` — T-18:
  `put_object` se llama con el objeto y su longitud reales, y la URL devuelta
  viene de `presigned_get_object` (firma `?X-Amz-Signature=`), no de la raíz
  fabricada `endpoint/bucket/key` del stub.
- `test_minio_unreachable_raises_clear_error_no_fake_url` — honestidad: si MinIO
  no responde (`put_object` lanza) → RuntimeError claro y NUNCA se devuelve una
  URL falsa (el stub anterior tragaba el error y devolvía la raíz igual).
- `test_helpers_keep_signature` — interfaz estable: `save_product_photo_to_minio`
  / `get_tenant_media_list` / `delete_tenant_media_item` conservan su firma
  (ingestion.py:159,189,198 dependen de ellas); el seed demo (hunk preservado)
  sigue listando items por tenant sin colisión.

Mocking: `minio.Minio` del módulo se reemplaza por un fake que registra
`put_object`/`presigned_get_object` — sin red ni servidor MinIO en los tests.
"""

import pytest

import backend.storage.minio_client as minio_module
from backend.storage.minio_client import (
    MinIOStorageClient,
    save_product_photo_to_minio,
    get_tenant_media_list,
    delete_tenant_media_item,
)


class FakeMinio:
    """Sustituto del SDK `minio.Minio`: registra llamadas y emite URLs firmadas."""

    def __init__(self, endpoint, access_key, secret_key, secure):
        self.endpoint = endpoint
        self.access_key = access_key
        self.bucket_exists_calls = []
        self.make_bucket_calls = []
        self.put_object_calls = []
        self.presigned_calls = []
        self.bucket_exists_result = True
        self.put_object_error = None

    def bucket_exists(self, bucket):
        self.bucket_exists_calls.append(bucket)
        return self.bucket_exists_result

    def make_bucket(self, bucket):
        self.make_bucket_calls.append(bucket)

    def put_object(self, bucket_name, object_name, data, length, content_type=None):
        self.put_object_calls.append((bucket_name, object_name, length, content_type))
        if self.put_object_error is not None:
            raise self.put_object_error
        return None

    def presigned_get_object(self, bucket_name, object_name, expires=None):
        self.presigned_calls.append((bucket_name, object_name))
        return (
            f"http://127.0.0.1:9000/{bucket_name}/{object_name}"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=fake&X-Amz-Signature=fake"
        )


@pytest.fixture
def fake_minio(monkeypatch):
    client = FakeMinio("minio:9000", "minioadmin", "minioadmin", False)
    monkeypatch.setattr(minio_module, "Minio", lambda *args, **kwargs: client)
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)
    return client


def test_upload_product_image_calls_put_object_and_returns_presigned(fake_minio):
    client = MinIOStorageClient()

    url = client.upload_product_image(
        b"fake_image_bytes_png", "foto producto.png", tenant_id="t-minio-01"
    )

    assert client.minio_client is fake_minio
    # put_object llamado con el objeto real y su longitud exacta
    assert len(fake_minio.put_object_calls) == 1
    bucket, object_key, length, content_type = fake_minio.put_object_calls[0]
    assert bucket == "viralsync-media"
    assert object_key == "t-minio-01/products/foto_producto.png"
    assert length == len(b"fake_image_bytes_png")
    assert content_type == "image/png"
    # La URL REAL es presignada (verdict T-00 #2: bucket PRIVADO), no la raíz fabricada
    assert "X-Amz-Signature=" in url
    assert "t-minio-01/products/foto_producto.png" in url
    assert fake_minio.presigned_calls == [("viralsync-media", "t-minio-01/products/foto_producto.png")]


def test_minio_unreachable_raises_clear_error_no_fake_url(fake_minio):
    fake_minio.put_object_error = ConnectionError("127.0.0.1:9000 connection refused")
    client = MinIOStorageClient()

    with pytest.raises(RuntimeError, match="MinIO"):
        client.upload_product_image(b"bytes", "foto.jpg", tenant_id="t-minio-02")

    # Nunca se firmó una URL para un objeto que no existe
    assert fake_minio.presigned_calls == []


def test_helpers_keep_signature(fake_minio):
    # list: seed demo (hunk preservado) para un tenant sin items
    items = get_tenant_media_list("t-minio-03")
    assert isinstance(items, list) and len(items) >= 1
    demo_id = f"vid-demo-{'t-minio-03'[:8]}-1"
    assert any(i["id"] == demo_id for i in items)

    # delete: elimina el item demo del registry
    deleted = delete_tenant_media_item("t-minio-03", demo_id)
    assert deleted is True

    # upload helper global: devuelve la URL REAL firmada
    url = save_product_photo_to_minio(b"bytes", "foto.jpg", tenant_id="t-minio-03")
    assert isinstance(url, str)
    assert "X-Amz-Signature=" in url
    assert "t-minio-03/products/foto.jpg" in url