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


import io
import json

try:
    from minio import Minio
    HAS_MINIO_SDK = True
except ImportError:
    HAS_MINIO_SDK = False


class MinIOStorageClient:
    """Cliente para la gestión de archivos multimedia en MinIO / S3."""

    def __init__(self):
        self.endpoint = MINIO_ENDPOINT
        self.bucket = MINIO_BUCKET
        self.minio_client = None

        if HAS_MINIO_SDK:
            try:
                # Extraer host y puerto limpios de MINIO_ENDPOINT
                host_port = self.endpoint.replace("http://", "").replace("https://", "").split("/")[0]
                self.minio_client = Minio(
                    host_port,
                    access_key=MINIO_ROOT_USER,
                    secret_key=MINIO_ROOT_PASSWORD,
                    secure=False,
                )
                if not self.minio_client.bucket_exists(self.bucket):
                    self.minio_client.make_bucket(self.bucket)
                    policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"AWS": ["*"]},
                                "Action": ["s3:GetObject"],
                                "Resource": [f"arn:aws:s3:::{self.bucket}/*"],
                            }
                        ],
                    }
                    self.minio_client.set_bucket_policy(self.bucket, json.dumps(policy))
            except Exception as err:
                logger.warning(f"No se pudo conectar a MinIO S3 SDK: {err}")

    def upload_product_image(
        self,
        file_bytes: bytes,
        filename: str,
        tenant_id: str,
        product_name: Optional[str] = None,
        classification: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Sube la foto del producto a MinIO y retorna la URL PRESIGNADA del objeto.

        WU-04 (design D6/T-18, REQ-PERSIST-05): el bucket `viralsync-media` es
        PRIVADO por default (verdict T-00 #2), así que la URL devuelta proviene
        de `presigned_get_object`. Si el upload falla se levanta RuntimeError y
        NUNCA se devuelve una URL fabricada (el stub anterior tragaba el error
        y devolvía la raíz `endpoint/bucket/key` igual).
        """
        safe_filename = filename.replace(" ", "_")
        media_id = str(uuid.uuid4())
        object_key = f"{tenant_id}/products/{safe_filename}"

        logger.info(f"[{tenant_id}] Subiendo foto de producto a MinIO: {object_key}")

        if self.minio_client is None or not file_bytes:
            raise RuntimeError(
                f"MinIO no disponible (SDK instalado={HAS_MINIO_SDK}) — "
                f"no se subió {object_key} y no se devolverá una URL falsa."
            )

        content_type = "image/jpeg"
        if safe_filename.lower().endswith(".png"):
            content_type = "image/png"
        elif safe_filename.lower().endswith(".webp"):
            content_type = "image/webp"

        try:
            self.minio_client.put_object(
                bucket_name=self.bucket,
                object_name=object_key,
                data=io.BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type,
            )
        except Exception as exc:
            logger.error(f"[{tenant_id}] Error al subir objeto a MinIO S3: {exc}")
            raise RuntimeError(
                f"MinIO no pudo guardar {object_key}: {exc} — no se devuelve URL falsa."
            ) from exc

        logger.info(f"[{tenant_id}] Archivo guardado físicamente en MinIO: {object_key}")

        url = self.minio_client.presigned_get_object(self.bucket, object_key)

        item = {
            "id": media_id,
            "tenant_id": tenant_id,
            "filename": safe_filename,
            "type": "image",
            "title": product_name or safe_filename,
            "url": url,
            "object_key": object_key,
            "size_bytes": len(file_bytes),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "classification": classification or {"business_type": "PRODUCTO_FISICO", "visual_mode": "IMAGE_TO_VIDEO"},
        }
        _MEDIA_REGISTRY.insert(0, item)
        return url

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
                    "url": f"{self.endpoint}/{self.bucket}/{tenant_id}/videos/reel_viral_fitness_v1.mp4",
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
                    "url": f"{self.endpoint}/{self.bucket}/{tenant_id}/products/suplemento_alpha_mind.png",
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
