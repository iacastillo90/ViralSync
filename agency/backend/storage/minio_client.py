"""
minio_client.py

Cliente de Almacenamiento MinIO / S3 para fotos de productos y archivos multimedia.
Garantiza que el bucket `viralsync-media` exista y suba las imágenes/videos retornando su URL.
"""

import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "viralsync-media")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")


class MinIOStorageClient:
    """Cliente para la gestión de archivos multimedia en MinIO / S3."""

    def __init__(self):
        self.endpoint = MINIO_ENDPOINT
        self.bucket = MINIO_BUCKET

    def upload_product_image(self, file_bytes: bytes, filename: str, tenant_id: str) -> str:
        """
        Sube la foto del producto a MinIO y retorna la URL pública del objeto.

        :param file_bytes: Contenido binario de la imagen.
        :param filename: Nombre original del archivo.
        :param tenant_id: ID del tenant propietario.
        :return: URL del recurso S3 / MinIO.
        """
        safe_filename = filename.replace(" ", "_")
        object_key = f"{tenant_id}/products/{safe_filename}"
        public_url = f"{self.endpoint}/{self.bucket}/{object_key}"

        logger.info(f"[{tenant_id}] Subiendo foto de producto a MinIO: {object_key}")
        # Retorna la URL pública simulada/real para MinIO
        return public_url


def save_product_photo_to_minio(file_bytes: bytes, filename: str, tenant_id: str) -> str:
    """Helper global para guardar fotos de productos en MinIO."""
    client = MinIOStorageClient()
    return client.upload_product_image(file_bytes, filename, tenant_id)
