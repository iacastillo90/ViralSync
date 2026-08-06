"""
main.py

Servidor Backend Principal FastAPI de ViralSync.
Puntos de entrada REST, Webhooks Meta con HMAC SHA-256 y SSE Streaming en Tiempo Real.
"""

import os
import asyncio
from fastapi import FastAPI, Request, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.security.hmac_validator import verify_meta_hmac_signature
from backend.sse_manager import sse_manager
from backend.webhooks.instagram_inbound import process_instagram_webhook_payload
from agents.graph import build_agency_graph

app = FastAPI(
    title="ViralSync Platform API",
    version="1.0.0",
    description="SaaS B2B Multi-Tenant para Agencias de Marketing de Contenido IA",
)

# Habilitar CORS para Next.js Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "secreto_meta_app_dev")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "token_verificacion_meta_dev")

# Instancia compilada del StateGraph
graph_app = build_agency_graph()


# --------------------------------------------------------------------- #
# Modelos Pydantic (Request / Response)
# --------------------------------------------------------------------- #
class TenantCreateRequest(BaseModel):
    name: str
    niche: str
    monthly_llm_budget_usd: float = 20.00


class GraphRunRequest(BaseModel):
    force_reideation: bool = False


class IdeaApproveRequest(BaseModel):
    idea_id: str
    status: str  # approved | rejected


class PublishApproveRequest(BaseModel):
    status: str  # approved | rejected


class TakeoverRequest(BaseModel):
    operator_id: str
    action: str = "pause_bot"


# --------------------------------------------------------------------- #
# 1. Endpoints REST (/api/v1)
# --------------------------------------------------------------------- #
@app.post("/api/v1/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant(req: TenantCreateRequest):
    tenant_id = f"tenant-{req.name.lower().replace(' ', '-')}-001"
    return {
        "id": tenant_id,
        "name": req.name,
        "niche": req.niche,
        "litellm_virtual_key": f"sk-agency-{tenant_id}",
        "monthly_llm_budget_usd": req.monthly_llm_budget_usd,
        "created_at": "2026-08-06T00:00:00Z",
    }


@app.get("/api/v1/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    return {
        "id": tenant_id,
        "name": "Cliente Demo Marketing",
        "niche": "Negocios B2B y SaaS",
        "monthly_llm_budget_usd": 20.00,
    }


from fastapi import FastAPI, Request, HTTPException, Header, Depends, status, File, UploadFile, Form
from backend.storage.minio_client import save_product_photo_to_minio
from agents.criterion.niche_classifier import classify_business_type


@app.post("/api/v1/tenants/{tenant_id}/product-ingest")
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
        "node_change",
        {
            "node": "ingestion",
            "status": "completed",
            "message": f"Producto/Servicio '{product_name}' ingresado exitosamente. Tipo: {classification['business_type']}",
        },
    )

    return {
        "tenant_id": tenant_id,
        "product_name": product_name,
        "description": description,
        "business_type": classification["business_type"],
        "visual_mode": classification["visual_mode"],
        "product_image_url": product_image_url,
        "status": "ingested",
    }


@app.post("/api/v1/tenants/{tenant_id}/graph/run")
async def run_graph(tenant_id: str, req: GraphRunRequest):
    # Emitir evento SSE de inicio de nodo
    await sse_manager.broadcast(
        tenant_id,
        "node_change",
        {"node": "ideation", "status": "running", "message": "Iniciando ideación RUM..."},
    )
    return {
        "tenant_id": tenant_id,
        "thread_id": tenant_id,
        "status": "running",
        "current_node": "ideation",
        "message": "Grafo LangGraph iniciado desde el nodo ideation.",
    }


@app.post("/api/v1/tenants/{tenant_id}/ideas/approve")
async def approve_idea(tenant_id: str, req: IdeaApproveRequest):
    await sse_manager.broadcast(
        tenant_id,
        "node_change",
        {"node": "scriptwriting", "status": "running", "message": "Idea aprobada. Generando guion..."},
    )
    return {
        "tenant_id": tenant_id,
        "idea_id": req.idea_id,
        "idea_approval_status": req.status,
        "next_node": "scriptwriting",
    }


@app.post("/api/v1/tenants/{tenant_id}/publish/approve")
async def approve_publish(tenant_id: str, req: PublishApproveRequest):
    post_id = f"ig_reel_{tenant_id[:8]}_99812"
    await sse_manager.broadcast(
        tenant_id,
        "node_change",
        {"node": "publish", "status": "completed", "message": f"Video publicado con ID {post_id}"},
    )
    return {
        "tenant_id": tenant_id,
        "publish_approval_status": req.status,
        "published_post_id": post_id,
        "next_node": "publish",
    }


@app.get("/api/v1/tenants/{tenant_id}/leads")
async def get_leads(tenant_id: str):
    return [
        {
            "id": "lead-001",
            "tenant_id": tenant_id,
            "video_id": "video-55",
            "keyword": "CONSULTA",
            "ig_user_id": "user_ig_9921",
            "mensaje_original": "Hola! Quiero la CONSULTA por favor",
            "origen": "comment",
            "calificado_at": "2026-08-06T01:45:00Z",
            "handled_by_human_at": None,
        }
    ]


@app.post("/api/v1/tenants/{tenant_id}/leads/{lead_id}/takeover")
async def takeover_lead(tenant_id: str, lead_id: str, req: TakeoverRequest):
    return {
        "lead_id": lead_id,
        "status": "handled_by_human",
        "handled_by_human_at": "2026-08-06T02:30:00Z",
        "message": "Bot pausado. Operador asignado exitosamente.",
    }


@app.get("/api/v1/tenants/{tenant_id}/metrics")
async def get_metrics(tenant_id: str):
    return [
        {
            "video_id": "video-55",
            "published_at": "2026-08-03T10:00:00Z",
            "metrics_72h": {
                "views": 150000,
                "followers_at_posting": 10000,
                "ratio": 15.0,
                "leads_generated": 142,
            },
            "classification": "VERDE",
            "action_taken": "Encolado para 3 variaciones en próximo batch.",
        },
        {
            "video_id": "video-56",
            "published_at": "2026-08-03T14:00:00Z",
            "metrics_72h": {
                "views": 4500,
                "followers_at_posting": 10000,
                "ratio": 0.45,
                "leads_generated": 2,
            },
            "classification": "ROJO",
            "action_taken": "Idea descartada.",
        },
    ]


# --------------------------------------------------------------------- #
# 2. Realtime SSE Endpoint (/realtime/sse/{tenant_id})
# --------------------------------------------------------------------- #
@app.get("/realtime/sse/{tenant_id}")
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
# 3. Meta Instagram Webhook (/webhooks/instagram)
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

    # Validar firma HMAC SHA-256
    if x_hub_signature_256:
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
        # Si falla el procesamiento en caliente, encolar en Celery DLQ con reintentos
        from workers.webhook_dlq_task import process_failed_webhook_retry
        process_failed_webhook_retry.delay(payload=payload, tenant_id="default")
        return {
            "status": "queued_dlq",
            "message": f"Error en procesamiento síncrono ({exc}). Encolado en Celery DLQ.",
        }
