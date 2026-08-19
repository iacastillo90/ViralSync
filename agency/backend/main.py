"""
main.py

Servidor Backend Principal FastAPI de ViralSync Enterprise.
Puntos de entrada REST modularizados por routers, Middleware de Aislamiento de Tenants,
Webhooks Meta HMAC y Streaming SSE en Tiempo Real.
"""

import os
import asyncio
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.security.hmac_validator import verify_meta_hmac_signature
from backend.security.auth import AGENCY_ENV, TenantContextMiddleware, verify_tenant_access
from backend.sse_manager import sse_manager
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload

from backend.logging_config import setup_logging
from backend.db.session import init_db
from backend.observability import setup_observability
from backend import __version__

# Importación de Routers Modularizados
from backend.routers.health import router as health_router
from backend.routers.ingestion import tenant_admin_router, ingestion_router
from backend.routers.graph_execution import router as graph_router, rebuild_graph_app
from backend.routers.leads import router as leads_router
from backend.routers.metrics import router as metrics_router
from backend.routers.ideas import router as ideas_router
from backend.routers.scripts import router as scripts_router
from backend.routers.brain import router as brain_router
from backend.routers.calendar import router as calendar_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.templates import router as templates_router
from backend.routers.rag import router as rag_router
from backend.routers.campaigns import router as campaigns_router
from backend.routers.ab_testing import router as ab_testing_router
from backend.routers.voice import router as voice_router
from backend.db.checkpointer import is_force_sqlite, setup_postgres_checkpointer, close_postgres_checkpointer

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Crea el esquema de base de datos en el arranque (idempotente via create_all).

    D2/T-14: en entornos PostgreSQL se abre la conexión async de larga vida del
    checkpointer (AsyncPostgresSaver, langgraph-checkpoint-postgres) y se
    reconstruye el graph_app con ella — thread_id=tenant_id, el estado de un run
    pausado sobrevive al restart del backend (PERSIST-04-1). Bajo
    FORCE_SQLITE=true (tests) el graph_app usa MemorySaver y NO se toca Postgres
    (PERSIST-04-2: el historial en memoria se descarta, sin migración).
    """
    await init_db()
    if not is_force_sqlite():
        await setup_postgres_checkpointer()
        rebuild_graph_app()
    yield
    if not is_force_sqlite():
        await close_postgres_checkpointer()

app = FastAPI(
    title="ViralSync Platform API Enterprise",
    version=__version__,
    description="SaaS B2B Multi-Tenant para Agencias de Marketing de Contenido IA",
    lifespan=lifespan,
)

setup_observability(app)




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
app.include_router(ideas_router, dependencies=_TENANT_GUARD)
app.include_router(scripts_router, dependencies=_TENANT_GUARD)
app.include_router(brain_router, dependencies=_TENANT_GUARD)
app.include_router(calendar_router, dependencies=_TENANT_GUARD)
app.include_router(dashboard_router, dependencies=_TENANT_GUARD)
app.include_router(rag_router, dependencies=_TENANT_GUARD)
app.include_router(campaigns_router, dependencies=_TENANT_GUARD)
app.include_router(ab_testing_router, dependencies=_TENANT_GUARD)
app.include_router(voice_router, dependencies=_TENANT_GUARD)
app.include_router(templates_router)

INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "secreto_meta_app_dev")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "token_verificacion_meta_dev")

# Security fail-fast guard (mirrors the JWT_SECRET_KEY guard in auth.py:27-28):
# in staging/prod a known default (or a missing env var that falls back to the
# default) for these Meta credentials must NOT be allowed to boot, otherwise an
# attacker can forge X-Hub-Signature-256 webhooks or pass hub.verify_token.
# Dev keeps the documented defaults so local onboarding keeps working.
if AGENCY_ENV in ["prod", "production", "staging"] and (
    INSTAGRAM_APP_SECRET == "secreto_meta_app_dev"
    or INSTAGRAM_VERIFY_TOKEN == "token_verificacion_meta_dev"
):
    raise ValueError(
        "CRÍTICO DE SEGURIDAD: INSTAGRAM_APP_SECRET / INSTAGRAM_WEBHOOK_VERIFY_TOKEN "
        "por defecto están prohibidos en entornos staging/prod. Configúrelos antes de arrancar."
    )


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
        except (asyncio.CancelledError, Exception):
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
        from backend.webhooks.instagram_inbound import _resolve_tenant_from_payload
        from workers.lead_persist_task import persist_instagram_lead

        # Resolución de tenant por cuenta (REQ-DM-LEAD-01) + enqueue del worker
        # (T-S1-06/07): el 200 al webhook queda desacoplado del trabajo async.
        tenant_id = await _resolve_tenant_from_payload(payload)
        extracted_leads = process_instagram_webhook_payload(payload, tenant_id=tenant_id)
        for lead_data in extracted_leads:
            persist_instagram_lead.delay(tenant_id, lead_data)
        return {
            "status": "ok",
            "processed_leads_count": len(extracted_leads),
            "leads": extracted_leads,
        }
    except Exception as exc:
        # RESILIENCE-001 (S1a2 review): no ackear 200 hacia una DLQ que no persiste.
        # Al devolver 500, Meta reintenta el webhook (redelivery) y el lead no se pierde.
        logger.error("Error en procesamiento síncrono del webhook de Instagram: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error en procesamiento síncrono del webhook de Instagram: {exc}",
        )
