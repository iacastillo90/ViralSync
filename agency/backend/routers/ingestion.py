"""
ingestion.py

Router de Ingesta dividido en dos APIRouter:
  - tenant_admin_router: endpoints de gestión administrativa de tenants (sin guard de tenant_id).
    Incluye: POST /api/v1/tenants (creación de tenant — endpoint público de registro).
  - ingestion_router: endpoints de ingesta de contenido por tenant (con verify_tenant_access).
    Incluye: POST /api/v1/tenants/{tenant_id}/product-ingest.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, File, UploadFile, Form, status, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.storage.minio_client import (
    build_object_key,
    save_product_photo_to_minio,
    get_tenant_media_list,
    delete_tenant_media_item,
)
from backend.db.daos import upsert_product
from agents.criterion.niche_classifier import classify_business_type
from backend.sse_manager import sse_manager
from backend.db.session import get_async_db
from backend.db.models import Tenant
from backend.security.auth import verify_tenant_access

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
    Returns the list of registered tenants.

    Listing policy (explicit for onboarding, documented):
    - Dev: public onboarding list, so the frontend boot flow (GET /tenants at
      boot) can render the tenant picker. NO sensitive per-tenant fields are
      exposed here: only the minimal public onboarding shape (id, name, niche).
    - Prod: the TenantContextMiddleware already requires a valid JWT for these
      paths, so only an authenticated caller can list. Sensitive internal
      fields (monthly_llm_budget_usd, litellm_virtual_key,
      instagram_graph_api_token_ref) must NEVER be aggregated back to the
      caller regardless of auth state.
    """
    result = await db.execute(select(Tenant))
    tenants = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "niche": t.niche,
        }
        for t in tenants
    ]


@tenant_admin_router.get("/{tenant_id}", status_code=status.HTTP_200_OK)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(verify_tenant_access),
):
    """
    Returns the details of a specific tenant.

    Tenant isolation (Anti-IDOR, OWASP A01): only a valid JWT whose tenant_id
    matches the requested tenant_id may read this tenant's profile. Reuses the
    same verify_tenant_access guard as every other tenant-scoped route:
    - mismatch JWT vs URL tenant -> 403
    - prod without a valid JWT -> 401 (fail-closed, verified by the middleware)
    - dev without JWT keeps the documented dev fallback (onboarding) -> 200
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
    # PERSIST-05-1 / D-5: la key ESTABLE del objeto (nunca la URL presignada que
    # expira). Se deriva con el MISMO helper del upload (sin drift) — la fila
    # `products` guarda la key; el graph la re-firma en cada lectura (SH-05-3).
    object_key = build_object_key(tenant_id, file.filename) if file else ""
    if file:
        content = await file.read()
        product_image_url = save_product_photo_to_minio(content, file.filename, tenant_id)
    # Sin archivo: product_image_url queda VACÍO (honestidad T-18/PERSIST-05-2).
    # Se eliminó el default muerto `.../products/default_product.jpg` — una URL
    # fabricada de un objeto que nunca se subió (mismo anti-patrón que el
    # s3:// del nodo publish, T-00 #3).

    classification = classify_business_type(description, user_choice=business_type)

    # REQ-PERSIST-05 / D8: el product-ingest persiste la fila `products` (upsert
    # por (tenant_id, name)) con los datos reales del form. Un fallo de DB es un
    # 503 honesto, nunca un payload state-only con falso éxito.
    try:
        await upsert_product(
            tenant_id,
            {
                "name": product_name,
                "description": description,
                "product_image_url": product_image_url,
                "object_key": object_key or None,
            },
        )
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error al persistir producto en DB: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error temporal de base de datos al guardar el producto.",
        )

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


@ingestion_router.get("/{tenant_id}/media")
async def list_media(tenant_id: str):
    """Lista los objetos REALES del tenant en MinIO (SH-01-1/2) — 200 siempre,
    lista vacía cuando no hay uploads (sin registry en memoria ni seeds demo)."""
    items = get_tenant_media_list(tenant_id)
    return items


@ingestion_router.delete("/{tenant_id}/media/{media_id:path}")
async def delete_media_item(tenant_id: str, media_id: str):
    """Elimina el objeto REAL de MinIO por object_key (REQ-SH-02).

    `media_id` == object_key (converter `:path` para claves con '/'; D-3). Solo
    se borra si pertenece al prefijo del tenant (guard SH-02-4, en el cliente);
    claves fuera del prefijo o desconocidas → 404 (SH-02-3). El delete es
    idempotente (S3 delete 204, SH-02-2)."""
    success = delete_tenant_media_item(tenant_id, media_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso multimedia no encontrado en MinIO")
    return {"status": "success", "deleted_media_id": media_id}
