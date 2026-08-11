"""
minio_client.py

Cliente de Almacenamiento MinIO / S3 para fotos de productos y archivos multimedia.
Garantiza que el bucket `viralsync-media` exista (PRIVADO) y gestione imágenes y
videos generados por tenant. Honestidad de almacenamiento (storage-honesty,
REQ-SH-01/02/03): list/delete contra MinIO REAL, config fail-fast, secure
derivado, sin registry en memoria ni seeds demo.
"""

import io
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "viralsync-media")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
# Host reachable desde el browser para URLs presignadas (SH-01-3, SH-05-3).
# Vacío por default → se firma contra el endpoint del contenedor.
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "")
MINIO_SECURE = os.getenv("MINIO_SECURE", "").lower() in ["true", "1", "yes"]

try:
    from minio import Minio
    HAS_MINIO_SDK = True
except ImportError:
    HAS_MINIO_SDK = False

AGENCY_ENV = os.getenv("AGENCY_ENV", "dev").lower()

# Fail-fast de credenciales por defecto en staging/prod (SH-03-1) — espejo de
# session.py:31-32 y main.py:107-114: misconfiguration debe fallar LOUD, no bootear
# con credenciales conocidas por defecto.
if AGENCY_ENV in ["prod", "production", "staging"] and (
    MINIO_ROOT_USER == "minioadmin" or MINIO_ROOT_PASSWORD == "minioadmin"
):
    raise ValueError(
        "SEGURIDAD: MINIO_ROOT_USER/MINIO_ROOT_PASSWORD por defecto ('minioadmin') "
        "están prohibidos en entornos staging/prod. Configúrelos antes de arrancar."
    )


def _derive_secure() -> bool:
    """secure = True si el endpoint es https:// o MINIO_SECURE es truthy (SH-03-2/3)."""
    return MINIO_SECURE or "https://" in MINIO_ENDPOINT


def _host_port(endpoint: str) -> str:
    """Extrae host:puerto limpio de un endpoint (http[s]:// opcional)."""
    return endpoint.replace("http://", "").replace("https://", "").split("/")[0]


class MinIOStorageClient:
    """Cliente para la gestión de archivos multimedia en MinIO / S3.

    Constructor = CONFIGURACIÓN PURA (D-1): no hace red, no crea el bucket.
    La creación perezosa del bucket ocurre en `_ensure_bucket()` en el primer
    upload (invariante de bucket PRIVADO preservado). Los errores de init/ops
    SIEMPRE se propagan — nunca un `minio_client=None` silencioso (SH-03-4).
    """

    def __init__(self):
        if not HAS_MINIO_SDK:
            raise RuntimeError(
                "MinIO SDK no instalado (HAS_MINIO_SDK=False) — el cliente de "
                "almacenamiento no puede inicializarse."
            )
        self.endpoint = MINIO_ENDPOINT
        self.bucket = MINIO_BUCKET
        self.secure = _derive_secure()
        self.public_endpoint = MINIO_PUBLIC_ENDPOINT
        self.minio_client = Minio(
            _host_port(MINIO_ENDPOINT),
            access_key=MINIO_ROOT_USER,
            secret_key=MINIO_ROOT_PASSWORD,
            secure=self.secure,
        )
        # Signer "público" opcional: si MINIO_PUBLIC_ENDPOINT está seteado, las
        # URLs presignadas se firman contra ese host (native signing, sin
        # string-surgery — D-1, SH-01-3).
        self._signer_client = None
        if self.public_endpoint:
            self._signer_client = Minio(
                _host_port(self.public_endpoint),
                access_key=MINIO_ROOT_USER,
                secret_key=MINIO_ROOT_PASSWORD,
                secure=self.secure,
            )

    # ── Bucket privado (lazy) ────────────────────────────────────────────────

    def _ensure_bucket(self) -> None:
        """Crea el bucket PRIVADO solo si no existe (lazy, primer upload)."""
        if not self.minio_client.bucket_exists(self.bucket):
            # RISK-01: el bucket se crea PRIVADO por default — nunca se aplica
            # una política pública; el acceso es solo vía URLs presignadas.
            self.minio_client.make_bucket(self.bucket)

    # ── Upload ───────────────────────────────────────────────────────────────

    def upload_product_image(
        self,
        file_bytes: bytes,
        filename: str,
        tenant_id: str,
        product_name: Optional[str] = None,
        classification: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Sube la foto del producto a MinIO y retorna la URL PRESIGNADA del objeto.

        Si el upload falla se levanta RuntimeError y NUNCA se devuelve una URL
        fabricada (el stub anterior tragaba el error y devolvía la raíz igual).
        """
        if not file_bytes:
            raise RuntimeError("MinIO no disponible — no se subió un archivo vacío.")
        safe_filename = filename.replace(" ", "_")
        object_key = build_object_key(tenant_id, safe_filename)

        logger.info(f"[{tenant_id}] Subiendo foto de producto a MinIO: {object_key}")

        content_type = "image/jpeg"
        if safe_filename.lower().endswith(".png"):
            content_type = "image/png"
        elif safe_filename.lower().endswith(".webp"):
            content_type = "image/webp"

        try:
            self._ensure_bucket()
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
        return self.presign(object_key)

    def presign(self, object_key: str) -> str:
        """Presigna el object_key contra el host correcto (public override o default)."""
        signer = self._signer_client or self.minio_client
        return signer.presigned_get_object(self.bucket, object_key)

    # ── List (honesto: MinIO es la única fuente de verdad) ───────────────────

    def list_tenant_media(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Lista los objetos REALES de MinIO bajo el prefijo `{tenant_id}/`.

        Un tenant sin uploads recibe [] (SH-01-2) — sin registry ni seeds demo.
        Cada item: {id, object_key, filename, type, url, size_bytes, created_at}
        con URL presignada (SH-01-1). `id` == `object_key` (D-3).
        """
        items: List[Dict[str, Any]] = []
        for obj in self.minio_client.list_objects(
            self.bucket, prefix=f"{tenant_id}/", recursive=True
        ):
            object_key = obj.object_name
            items.append(self._to_media_item(object_key, obj))
        return items

    def _to_media_item(self, object_key: str, obj) -> Dict[str, Any]:
        filename = object_key.rsplit("/", 1)[-1]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        media_type = "video" if ext in ("mp4", "mov", "avi", "mkv", "webm") else "image"
        return {
            "id": object_key,
            "object_key": object_key,
            "filename": filename,
            "title": filename,
            "type": media_type,
            "url": self.presign(object_key),
            "size_bytes": getattr(obj, "size", 0),
            "created_at": MinIOStorageClient._iso_last_modified(
                getattr(obj, "last_modified", None)
            ),
        }

    @staticmethod
    def _iso_last_modified(value) -> str:
        if value is None:
            return datetime.now(timezone.utc).isoformat()
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    # ── Delete (honesto + guard de prefijo) ──────────────────────────────────

    def delete_media(self, tenant_id: str, media_id: str) -> bool:
        """Elimina el objeto real de MinIO con guard de prefijo de tenant (SH-02-4).

        `media_id` es el object_key (D-3): solo se borra si empieza con
        `{tenant_id}/`. remove_object es idempotente (S3 delete 204) → repetir
        devuelve True (SH-02-2). Claves fuera del prefijo → False (404 en API).
        """
        if not media_id.startswith(f"{tenant_id}/"):
            logger.warning(
                f"[{tenant_id}] Delete rehusado: {media_id} está fuera del prefijo del tenant."
            )
            return False
        try:
            self.minio_client.remove_object(self.bucket, media_id)
        except Exception as exc:
            logger.error(f"[{tenant_id}] Error al eliminar objeto de MinIO: {exc}")
            raise RuntimeError(f"MinIO no pudo eliminar {media_id}: {exc}") from exc
        return True


# ── Singleton cacheado (D-1) ──────────────────────────────────────────────────

_client: Optional[MinIOStorageClient] = None


def get_client() -> MinIOStorageClient:
    """Singleton cacheado a nivel de módulo. Lanza si SDK/credenciales fallan —
    nunca un `minio_client=None` silencioso (SH-03-4)."""
    global _client
    if _client is None:
        _client = MinIOStorageClient()
    return _client


def _reset_client() -> None:
    """Hook de test: descarta el singleton cacheado."""
    global _client
    _client = None


# ── Helpers compartidos (firmas preservadas, D-1) ────────────────────────────

def build_object_key(tenant_id: str, filename: str) -> str:
    """Deriva el object_key estable de un tenant + filename (D-1, sin drift)."""
    safe = filename.replace(" ", "_")
    return f"{tenant_id}/products/{safe}"


def presign_public_url(object_key: str) -> str:
    """Presigna un object_key honrando MINIO_PUBLIC_ENDPOINT (SH-01-3, SH-05-3)."""
    return get_client().presign(object_key)


def save_product_photo_to_minio(
    file_bytes: bytes,
    filename: str,
    tenant_id: str,
    product_name: Optional[str] = None,
    classification: Optional[Dict[str, Any]] = None,
) -> str:
    """Helper global para guardar fotos de productos en MinIO (firma preservada)."""
    return get_client().upload_product_image(
        file_bytes, filename, tenant_id, product_name, classification
    )


def get_tenant_media_list(tenant_id: str) -> List[Dict[str, Any]]:
    """Helper global para listar recursos multimedia de un tenant (firma preservada)."""
    return get_client().list_tenant_media(tenant_id)


def delete_tenant_media_item(tenant_id: str, media_id: str) -> bool:
    """Helper global para eliminar un recurso de MinIO (firma preservada)."""
    return get_client().delete_media(tenant_id, media_id)
