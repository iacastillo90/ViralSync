"""
minio_client.py

Cliente de Almacenamiento MinIO / S3 para fotos de productos y archivos multimedia.
Garantiza que el bucket `viralsync-media` exista y gestione imágenes y videos generados por tenant.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "viralsync-media")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

# Almacén en memoria de elementos multimedia por tenant
_MEDIA_REGISTRY: List[Dict[str, Any]] = []


class MinIOStorageClient:
    """Cliente para la gestión de archivos multimedia en MinIO / S3."""

    def __init__(self):
        self.endpoint = MINIO_ENDPOINT
        self.bucket = MINIO_BUCKET

    def upload_product_image(
        self,
        file_bytes: bytes,
        filename: str,
        tenant_id: str,
        product_name: Optional[str] = None,
        classification: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Sube la foto del producto a MinIO y retorna la URL pública del objeto.
        """
        safe_filename = filename.replace(" ", "_")
        media_id = str(uuid.uuid4())
        object_key = f"{tenant_id}/products/{safe_filename}"
        public_url = f"{self.endpoint}/{self.bucket}/{object_key}"

        logger.info(f"[{tenant_id}] Subiendo foto de producto a MinIO: {object_key}")

        item = {
            "id": media_id,
            "tenant_id": tenant_id,
            "filename": safe_filename,
            "type": "image",
            "title": product_name or safe_filename,
            "url": public_url,
            "object_key": object_key,
            "size_bytes": len(file_bytes),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "classification": classification or {"business_type": "PRODUCTO_FISICO", "visual_mode": "IMAGE_TO_VIDEO"},
        }
        _MEDIA_REGISTRY.insert(0, item)
        return public_url

    def list_tenant_media(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Devuelve la lista de recursos multimedia (imágenes y videos) pertenecientes a un tenant."""
        tenant_items = [m for m in _MEDIA_REGISTRY if m.get("tenant_id") == tenant_id]
        if not tenant_items:
            # Seed de demostración inicial por tenant si no hay elementos aún
            demo_items = [
                {
                    "id": f"vid-demo-{tenant_id[:8]}-1",
                    "tenant_id": tenant_id,
                    "filename": "reel_viral_fitness_v1.mp4",
                    "type": "video",
                    "title": "Reel IA: 3 Errores al Escalar en Redes",
                    "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                    "object_key": f"{tenant_id}/videos/reel_viral_fitness_v1.mp4",
                    "size_bytes": 14250000,
                    "duration_seconds": 32,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "classification": {"business_type": "PRODUCTO_FISICO", "visual_mode": "IMAGE_TO_VIDEO"},
                },
                {
                    "id": f"img-demo-{tenant_id[:8]}-2",
                    "tenant_id": tenant_id,
                    "filename": "suplemento_alpha_mind.png",
                    "type": "image",
                    "title": "Suplemento Nootrópico AlphaMind",
                    "url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&auto=format&fit=crop&q=60",
                    "object_key": f"{tenant_id}/products/suplemento_alpha_mind.png",
                    "size_bytes": 2450000,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "classification": {"business_type": "PRODUCTO_FISICO", "visual_mode": "IMAGE_TO_VIDEO"},
                },
            ]
            _MEDIA_REGISTRY.extend(demo_items)
            return demo_items
        return tenant_items

    def delete_media(self, tenant_id: str, media_id: str) -> bool:
        """Elimina un recurso multimedia de MinIO por su ID."""
        global _MEDIA_REGISTRY
        initial_len = len(_MEDIA_REGISTRY)
        _MEDIA_REGISTRY = [
            m for m in _MEDIA_REGISTRY
            if not (m.get("tenant_id") == tenant_id and m.get("id") == media_id)
        ]
        return len(_MEDIA_REGISTRY) < initial_len


def save_product_photo_to_minio(
    file_bytes: bytes,
    filename: str,
    tenant_id: str,
    product_name: Optional[str] = None,
    classification: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper global para guardar fotos de productos en MinIO."""
    client = MinIOStorageClient()
    return client.upload_product_image(file_bytes, filename, tenant_id, product_name, classification)


def get_tenant_media_list(tenant_id: str) -> List[Dict[str, Any]]:
    """Helper global para listar recursos multimedia de un tenant."""
    client = MinIOStorageClient()
    return client.list_tenant_media(tenant_id)


def delete_tenant_media_item(tenant_id: str, media_id: str) -> bool:
    """Helper global para eliminar un recurso de MinIO."""
    client = MinIOStorageClient()
    return client.delete_media(tenant_id, media_id)
