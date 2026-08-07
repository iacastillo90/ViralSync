"""
main.py

Servidor Backend Principal FastAPI de ViralSync Enterprise.
Puntos de entrada REST modularizados por routers, Middleware de Aislamiento de Tenants,
Webhooks Meta HMAC y Streaming SSE en Tiempo Real.
"""

import os
import asyncio
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.security.hmac_validator import verify_meta_hmac_signature
from backend.security.auth import TenantContextMiddleware, verify_tenant_access
from backend.sse_manager import sse_manager
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload

from backend.logging_config import setup_logging
from backend.db.session import init_db

# Importación de Routers Modularizados
from backend.routers.health import router as health_router
from backend.routers.ingestion import tenant_admin_router, ingestion_router
from backend.routers.graph_execution import router as graph_router
from backend.routers.leads import router as leads_router
from backend.routers.metrics import router as metrics_router

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Crea el esquema de base de datos en el arranque (idempotente via create_all)."""
    await init_db()
    yield


app = FastAPI(
    title="ViralSync Platform API Enterprise",
    version="1.0.0",
    description="SaaS B2B Multi-Tenant para Agencias de Marketing de Contenido IA",
    lifespan=lifespan,
)



ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
is_dev = os.getenv("AGENCY_ENV", "dev") == "dev"

# 1. Habilitar CORS para Next.js Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_dev else ALLOWED_ORIGINS,
    allow_credentials=False if is_dev else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Habilitar Middleware de Aislamiento de Tenant
app.add_middleware(TenantContextMiddleware)

# 3. Registrar Routers Modularizados
# verify_tenant_access se aplica como dependencia sistémica a todos los routers bajo
# /tenants/{tenant_id}/* para garantizar aislamiento Anti-IDOR por diseño —
# cualquier endpoint nuevo queda protegido sin necesidad de llamadas manuales.
_TENANT_GUARD = [Depends(verify_tenant_access)]

app.include_router(health_router)
app.include_router(tenant_admin_router)            # Sin guard: POST /tenants (registro público)
app.include_router(ingestion_router, dependencies=_TENANT_GUARD)
app.include_router(graph_router, dependencies=_TENANT_GUARD)
app.include_router(leads_router, dependencies=_TENANT_GUARD)
app.include_router(metrics_router, dependencies=_TENANT_GUARD)

INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "secreto_meta_app_dev")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "token_verificacion_meta_dev")


# --------------------------------------------------------------------- #
# Realtime SSE Endpoint (/realtime/sse/{tenant_id})
# --------------------------------------------------------------------- #
@app.get("/realtime/sse/{tenant_id}", dependencies=[Depends(verify_tenant_access)])
async def sse_endpoint(tenant_id: str, request: Request):
    queue = sse_manager.subscribe(tenant_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                payload = await queue.get()
                yield payload
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unsubscribe(tenant_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --------------------------------------------------------------------- #
# Meta Instagram Webhook (/webhooks/instagram)
# --------------------------------------------------------------------- #
@app.get("/webhooks/instagram")
async def verify_instagram_webhook(
    hub_mode: Optional[str] = Header(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Header(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Header(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == INSTAGRAM_VERIFY_TOKEN:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="Verify token inválido")


@app.post("/webhooks/instagram")
async def receive_instagram_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    body_bytes = await request.body()

    env = os.getenv("AGENCY_ENV", "dev")

    # Validación HMAC obligatoria — el bypass de omitir el header es una vulnerabilidad crítica.
    # En producción rechazamos inmediatamente si el header no está presente.
    if not x_hub_signature_256:
        if env != "dev":
            raise HTTPException(
                status_code=401,
                detail="Firma HMAC requerida: header X-Hub-Signature-256 ausente",
            )
    else:
        is_valid = verify_meta_hmac_signature(
            payload_bytes=body_bytes,
            signature_header=x_hub_signature_256,
            app_secret=INSTAGRAM_APP_SECRET,
        )
        if not is_valid:
            raise HTTPException(status_code=401, detail="Firma HMAC SHA-256 inválida")

    payload = await request.json()

    try:
        extracted_leads = process_instagram_webhook_payload(payload)
        return {
            "status": "ok",
            "processed_leads_count": len(extracted_leads),
            "leads": extracted_leads,
        }
    except Exception as exc:
        from workers.webhook_dlq_task import process_failed_webhook_retry
        process_failed_webhook_retry.delay(payload=payload, tenant_id="default")
        return {
            "status": "queued_dlq",
            "message": f"Error en procesamiento síncrono ({exc}). Encolado en Celery DLQ.",
        }
