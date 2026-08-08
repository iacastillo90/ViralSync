"""
ingestion.py

Router de Ingesta dividido en dos APIRouter:
  - tenant_admin_router: endpoints de gestión administrativa de tenants (sin guard de tenant_id).
    Incluye: POST /api/v1/tenants (creación de tenant — endpoint público de registro).
  - ingestion_router: endpoints de ingesta de contenido por tenant (con verify_tenant_access).
    Incluye: POST /api/v1/tenants/{tenant_id}/product-ingest.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, Form, status, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.storage.minio_client import save_product_photo_to_minio
from agents.criterion.niche_classifier import classify_business_type
from backend.sse_manager import sse_manager
from backend.db.session import get_async_db
from backend.db.models import Tenant

logger = logging.getLogger(__name__)


class TenantCreateRequest(BaseModel):
    name: str
    niche: str
    monthly_llm_budget_usd: float = 20.00


# ─── Router 1: Administración de Tenants (sin guard de tenant_id) ─────────────
# Estos endpoints no requieren un tenant_id existente en el path — son el punto
# de entrada para crear nuevos tenants. No deben tener verify_tenant_access.
tenant_admin_router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Admin"])


@tenant_admin_router.get("", status_code=status.HTTP_200_OK)
async def list_tenants(db: AsyncSession = Depends(get_async_db)):
    """
    Retorna la lista completa de tenants registrados en el sistema.
    """
    result = await db.execute(select(Tenant))
    tenants = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "niche": t.niche,
            "monthly_llm_budget_usd": t.monthly_llm_budget_usd,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tenants
    ]


@tenant_admin_router.get("/{tenant_id}", status_code=status.HTTP_200_OK)
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_async_db)):
    """
    Retorna los detalles de un tenant específico.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    t = result.scalars().first()
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant con ID {tenant_id} no encontrado en la base de datos."
        )
    return {
        "id": t.id,
        "name": t.name,
        "niche": t.niche,
        "monthly_llm_budget_usd": t.monthly_llm_budget_usd,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@tenant_admin_router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(req: TenantCreateRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Crea un nuevo tenant en Postgres con UUID real y clave LiteLLM virtual segura.
    Endpoint público de registro — no requiere JWT previo (es el paso de onboarding).
    """
    import uuid
    import secrets
    from datetime import datetime, timezone

    tenant_id = str(uuid.uuid4())
    # Clave virtual segura con 32 bytes aleatorios — NO fabricada a partir del tenant_id
    litellm_virtual_key = f"sk-vs-{secrets.token_urlsafe(24)}"
    
    # Crear registro del tenant en PostgreSQL
    new_tenant = Tenant(
        id=tenant_id,
        name=req.name,
        niche=req.niche,
        litellm_virtual_key=litellm_virtual_key,
        monthly_llm_budget_usd=req.monthly_llm_budget_usd,
    )
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)

    logger.info(f"Persistido nuevo tenant en Postgres: {tenant_id} (name={req.name}, niche={req.niche})")

    return {
        "id": tenant_id,
        "name": req.name,
        "niche": req.niche,
        "litellm_virtual_key": litellm_virtual_key,
        "monthly_llm_budget_usd": req.monthly_llm_budget_usd,
        "created_at": new_tenant.created_at.isoformat() if new_tenant.created_at else datetime.now(timezone.utc).isoformat(),
    }



# ─── Router 2: Ingesta de Contenido por Tenant (con verify_tenant_access) ─────
# Todos los endpoints aquí operan sobre un tenant_id existente y deben pasar
# el guard sistémico de aislamiento Anti-IDOR registrado en main.py.
ingestion_router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Ingestion"])


@ingestion_router.post("/{tenant_id}/product-ingest")
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
        product_image_url = (
            f"http://localhost:9000/viralsync-media/{tenant_id}/products/default_product.jpg"
        )

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
