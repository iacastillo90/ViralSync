"""
test_presigned_ingestion.py

Pruebas unitarias para la generación de presigned upload URLs (REQ-PSI-01).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.storage.minio_client import MinIOStorageClient


def test_minio_client_get_presigned_upload_url():
    """Verifica que get_presigned_upload_url genere la clave de objeto y devuelva el dict esperado."""
    client = MinIOStorageClient.__new__(MinIOStorageClient)
    client.bucket = "viralsync-media"
    client._signer_client = None
    
    mock_minio = MagicMock()
    mock_minio.presigned_put_object.return_value = "http://localhost:9000/viralsync-media/tenant_abc/products/foto.jpg?signature=123"
    client.minio_client = mock_minio
    client._ensure_bucket = MagicMock()
    
    result = client.get_presigned_upload_url("tenant_abc", "foto.jpg", expires_in_seconds=1800)
    
    assert result["tenant_id"] == "tenant_abc"
    assert result["object_key"] == "tenant_abc/products/foto.jpg"
    assert result["expires_in"] == 1800
    assert "upload_url" in result
    mock_minio.presigned_put_object.assert_called_once()
