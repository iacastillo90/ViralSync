"""
ingestion.py

Router para la Creación de Tenants y la Ingesta de Productos/Servicios.
"""

from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, status
from pydantic import BaseModel
from backend.storage.minio_client import save_product_photo_to_minio
from agents.criterion.niche_classifier import classify_business_type
from backend.sse_manager import sse_manager

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant & Ingestion"])


class TenantCreateRequest(BaseModel):
    name: str
    niche: str
    monthly_llm_budget_usd: float = 20.00


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(req: TenantCreateRequest):
    """Crea un nuevo tenant registrando sus claves virtuales y presupuesto."""
    tenant_id = f"tenant-{req.name.lower().replace(' ', '-')}-001"
    return {
        "id": tenant_id,
        "name": req.name,
        "niche": req.niche,
        "litellm_virtual_key": f"sk-agency-{tenant_id}",
        "monthly_llm_budget_usd": req.monthly_llm_budget_usd,
        "created_at": "2026-08-06T00:00:00Z",
    }


@router.post("/{tenant_id}/product-ingest")
async def ingest_product_data(
    tenant_id: str,
    product_name: str = Form(...),
    description: str = Form(...),
    business_type: str = Form("auto"),
    file: Optional[UploadFile] = File(None),
):
    """Sube la foto del producto a MinIO y clasifica si es Producto Físico o Servicio Intangible."""
    product_image_url = ""
    if file:
        content = await file.read()
        product_image_url = save_product_photo_to_minio(content, file.filename, tenant_id)
    else:
        product_image_url = f"http://localhost:9000/viralsync-media/{tenant_id}/products/default_product.jpg"

    classification = classify_business_type(description, user_choice=business_type)

    await sse_manager.broadcast(
        tenant_id,
        "ingest_complete",
        {
            "product_name": product_name,
            "classification": classification,
            "product_image_url": product_image_url,
        },
    )

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "product_name": product_name,
        "classification": classification,
        "product_image_url": product_image_url,
    }
