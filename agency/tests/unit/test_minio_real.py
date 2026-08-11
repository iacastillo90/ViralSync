"""
test_minio_real.py

Real MinIO upload tests for WU-04 (design D6, T-00 verdict #2, REQ-PERSIST-05)
and storage-honesty (REQ-SH-01/02/03, slice 1):
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
  (ingestion.py depende de ellas), pero ahora operan sobre MinIO REAL:
  list = `list_objects(prefix={tenant}/)` (FakeMinio vacío → []), delete =
  `remove_object` con guard de prefijo (idempotente), upload = URL firmada.
  Sin registry en memoria ni seeds demo (SH-01-2).

Mocking: `minio.Minio` del módulo se reemplaza por un fake que registra
`put_object`/`presigned_get_object`/`list_objects`/`remove_object` — sin red ni
servidor MinIO en los tests.
"""

from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

import backend.storage.minio_client as minio_module
from backend.storage.minio_client import (
    MinIOStorageClient,
    save_product_photo_to_minio,
    get_tenant_media_list,
    delete_tenant_media_item,
)


class FakeMinio:
    """Sustituto del SDK `minio.Minio`: registra llamadas y emite URLs firmadas.

    Lista/elimina objetos REALES (dict `objects` por object_name) — los tests
    de honestidad (storage-honesty) verifican que list/delete hablan con MinIO
    y no con un registry en memoria.
    """

    def __init__(self, endpoint, access_key, secret_key, secure):
        self.endpoint = endpoint
        self.access_key = access_key
        self.bucket_exists_calls = []
        self.make_bucket_calls = []
        self.put_object_calls = []
        self.presigned_calls = []
        self.list_objects_calls = []
        self.remove_object_calls = []
        self.bucket_exists_result = True
        self.put_object_error = None
        self.objects = {}

    def bucket_exists(self, bucket):
        self.bucket_exists_calls.append(bucket)
        return self.bucket_exists_result

    def make_bucket(self, bucket):
        self.make_bucket_calls.append(bucket)

    def put_object(self, bucket_name, object_name, data, length, content_type=None):
        self.put_object_calls.append((bucket_name, object_name, length, content_type))
        if self.put_object_error is not None:
            raise self.put_object_error
        self.objects[object_name] = {
            "size": length,
            "last_modified": datetime.now(timezone.utc),
        }
        return None

    def list_objects(self, bucket_name, prefix=None, recursive=False):
        self.list_objects_calls.append((bucket_name, prefix, recursive))
        return [
            SimpleNamespace(object_name=key, size=meta["size"], last_modified=meta["last_modified"])
            for key, meta in self.objects.items()
            if prefix is None or key.startswith(prefix)
        ]

    def remove_object(self, bucket_name, object_name):
        self.remove_object_calls.append((bucket_name, object_name))
        self.objects.pop(object_name, None)  # idempotente (S3 delete 204)

    def presigned_get_object(self, bucket_name, object_name, expires=None):
        self.presigned_calls.append((bucket_name, object_name))
        return (
            f"http://{self.endpoint}/{bucket_name}/{object_name}"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=fake&X-Amz-Signature=fake"
        )


@pytest.fixture
def fake_minio(monkeypatch):
    client = FakeMinio("minio:9000", "minioadmin", "minioadmin", False)
    monkeypatch.setattr(minio_module, "Minio", lambda *args, **kwargs: client)
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)
    return client


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    """Descarta el singleton cacheado de get_client() antes/después de cada test
    para que cada test reciba un cliente fresco ligado a SU FakeMinio."""
    minio_module._reset_client()
    yield
    minio_module._reset_client()


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


def test_presign_honors_public_endpoint_override(monkeypatch):
    """SH-01-3: MINIO_PUBLIC_ENDPOINT seteado → las URLs presignadas se firman
    contra ese host (signer bound), no contra el endpoint del contenedor."""
    default = FakeMinio("minio:9000", "minioadmin", "minioadmin", False)
    signer = FakeMinio("public.example.com", "minioadmin", "minioadmin", False)
    created = {"count": 0}

    def factory(*args, **kwargs):
        created["count"] += 1
        return signer if created["count"] == 2 else default

    monkeypatch.setattr(minio_module, "Minio", factory)
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)
    monkeypatch.setattr(minio_module, "MINIO_PUBLIC_ENDPOINT", "http://public.example.com")

    client = minio_module.MinIOStorageClient()
    url = client.presign("t-01/products/foto.jpg")

    assert url.startswith("http://public.example.com/viralsync-media/")
    assert "X-Amz-Signature=" in url
    # El signer (2º Minio) es el que firmó — nunca el cliente default
    assert signer.presigned_calls == [("viralsync-media", "t-01/products/foto.jpg")]
    assert default.presigned_calls == []


def test_helpers_keep_signature(fake_minio):
    # list: FakeMinio vacío → [] — sin registry ni seeds demo (SH-01-2), y el
    # listado honesto consulta el bucket bajo el prefijo del tenant (SH-01-1)
    items = get_tenant_media_list("t-minio-03")
    assert items == []
    assert fake_minio.list_objects_calls == [("viralsync-media", "t-minio-03/", True)]

    # delete: clave dentro del prefijo del tenant → remove_object + True
    # (idempotente, SH-02-2); NUNCA filtra un registry en memoria
    deleted = delete_tenant_media_item("t-minio-03", "t-minio-03/products/foto.jpg")
    assert deleted is True
    assert fake_minio.remove_object_calls == [("viralsync-media", "t-minio-03/products/foto.jpg")]

    # upload helper global: devuelve la URL REAL firmada
    url = save_product_photo_to_minio(b"bytes", "foto.jpg", tenant_id="t-minio-03")
    assert isinstance(url, str)
    assert "X-Amz-Signature=" in url
    assert "t-minio-03/products/foto.jpg" in url