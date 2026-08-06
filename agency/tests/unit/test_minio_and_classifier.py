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


def test_minio_storage_client_upload():
    client = MinIOStorageClient()
    file_bytes = b"fake_image_bytes"
    filename = "zapatilla running.png"
    url = client.upload_product_image(file_bytes, filename, tenant_id="tenant-test")
    assert "viralsync-media" in url
    assert "zapatilla_running.png" in url
    assert "tenant-test/products/" in url
