"""
test_minio_and_classifier.py

Pruebas unitarias para la integración de MinIO y el Clasificador Inteligente Producto vs Servicio.
"""

from backend.storage.minio_client import save_product_photo_to_minio, MinIOStorageClient
from agents.criterion.niche_classifier import classify_business_type


def test_classify_business_type_product():
    description = "Zapatillas deportivas para running con suela de gel y amortiguación física."
    result = classify_business_type(description, user_choice="auto")
    assert result["business_type"] == "PRODUCTO_FISICO"
    assert result["visual_mode"] == "IMAGE_TO_VIDEO"


def test_classify_business_type_service():
    description = "Consultoría estratégica de crecimiento B2B para agencias y SaaS."
    result = classify_business_type(description, user_choice="auto")
    assert result["business_type"] == "SERVICIO_INTANGIBLE"
    assert result["visual_mode"] == "TEXT_TO_VIDEO"


def test_minio_storage_client_upload(monkeypatch):
    """WU-04 (D6/T-18): el upload real devuelve URL presignada y llama a put_object.

    Comportamiento honesto: con el bucket PRIVADO por default (verdict T-00 #2)
    la URL viene de `presigned_get_object` — nunca la raíz fabricada
    `endpoint/bucket/key` que devolvía el stub cuando el upload fallaba.
    """

    class FakeMinio:
        def __init__(self, *args, **kwargs):
            self.put_object_calls = []
            self.presigned_calls = []
            # MinIOStorageClient precarga la región por bucket (SigV4 us-east-1)
            # en `_region_map` durante __init__ (ver minio_client.py).
            self._region_map: dict = {}

        def bucket_exists(self, bucket):
            return True

        def put_object(self, bucket_name, object_name, data, length, content_type=None):
            self.put_object_calls.append((bucket_name, object_name, length))

        def presigned_get_object(self, bucket_name, object_name, expires=None):
            self.presigned_calls.append((bucket_name, object_name))
            return (
                f"http://localhost:9000/{bucket_name}/{object_name}"
                "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=fake"
            )

    import backend.storage.minio_client as minio_module
    from backend.storage.minio_client import MinIOStorageClient

    monkeypatch.setattr(minio_module, "Minio", lambda *a, **kw: FakeMinio())
    monkeypatch.setattr(minio_module, "HAS_MINIO_SDK", True)

    client = MinIOStorageClient()
    file_bytes = b"fake_image_bytes"
    filename = "zapatilla running.png"
    url = client.upload_product_image(file_bytes, filename, tenant_id="tenant-test")

    # Mismas subcadenas de contrato que antes (endpoint/bucket/path del objeto)…
    assert "viralsync-media" in url
    assert "zapatilla_running.png" in url
    assert "tenant-test/products/" in url
    # …pero ahora la URL es REAL y firmada (bucket privado), y put_object se llamó
    assert "X-Amz-Signature=" in url
    assert client.minio_client.put_object_calls[0][1] == "tenant-test/products/zapatilla_running.png"
