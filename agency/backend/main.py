"""
backend/main.py

Servidor FastAPI unificado para la Agencia Multiagente de Marketing.
Conecta endpoints REST, streaming SSE, webhooks de Instagram y orquestación con LangGraph.
"""

import os
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.realtime.sse_manager import sse_manager
from backend.webhooks.instagram_inbound import router as instagram_webhook_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agency.backend")

app = FastAPI(
    title="Agency Multi-Agent Marketing API",
    version="1.0.0",
    description="Backend FastAPI multi-tenant para orquestación de agencia de marketing.",
)

# Habilitar CORS para el frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir router de webhooks de Instagram con firma HMAC y verificaciones
app.include_router(instagram_webhook_router, prefix="/webhooks", tags=["webhooks"])

# Base de datos en memoria para estado y ejecuciones en modo local/dev
TENANTS_DB = {
    "tenant-demo-001": {
        "id": "tenant-demo-001",
        "name": "Cliente Demo Marketing",
        "niche": "Negocios B2B y SaaS",
        "litellm_virtual_key": "sk-agency-demo-key",
        "monthly_llm_budget_usd": 20.00,
        "state": {
            "node": "human_approval_idea",
            "idea_approval_status": "pending",
            "candidate_ideas": [
                {
                    "id": "idea-101",
                    "texto": "3 Errores fatales en Negocios B2B que te están costando clientes",
                    "gancho": "Si trabajas en Negocios B2B, deja de hacer esto inmediatamente...",
                    "universalidad": 0.85,
                    "intensidad": 0.90,
                    "claridad": 0.95,
                    "shareability": 0.80,
                    "distribucion": 0.85,
                    "alineacion": 0.90,
                    "rum_score": 0.444,
                    "passes_threshold": True,
                }
            ],
            "rum_threshold": 0.050,
            "script": {
                "gancho_0_5s": "¡Detente! Si quieres escalar tu SaaS B2B, necesitas esto.",
                "contexto_5_30s": "La mayoría comete el error de enfocarse en alcance frío sin entender la retención del algoritmo...",
                "moraleja_30_50s": "La clave está en automatizar la calificacion de leads con respuestas inmediatas.",
                "cta_50_60s": "Comenta la palabra 'CONSULTA' abajo y te enviaré la guía completa.",
                "keyword": "CONSULTA",
            },
            "raw_video_uri": "/storage/raw/sample_video.mp4",
            "edited_video_uri": "/storage/videos/edited_sample_video.mp4",
            "publish_approval_status": "pending",
        },
    }
}

LEADS_DB = [
    {
        "id": "lead-001",
        "tenant_id": "tenant-demo-001",
        "video_id": "video-55",
        "keyword": "CONSULTA",
        "ig_user_id": "user_ig_9921",
        "mensaje_original": "Hola! Quiero la CONSULTA por favor",
        "origen": "comment",
        "calificado_at": "2026-08-05T22:15:00Z",
        "handled_by_human_at": None,
        "outcome": None,
    }
]


@app.get("/health")
def health_check():
    return {"status": "ok", "env": os.getenv("AGENCY_ENV", "dev")}


@app.get("/tenants")
def list_tenants():
    return list(TENANTS_DB.values())


@app.post("/tenants")
def create_tenant(name: str, niche: str, budget: float = 20.0):
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    tenant_data = {
        "id": tenant_id,
        "name": name,
        "niche": niche,
        "litellm_virtual_key": f"sk-agency-{tenant_id}",
        "monthly_llm_budget_usd": budget,
        "state": {"node": "ideation", "candidate_ideas": []},
    }
    TENANTS_DB[tenant_id] = tenant_data
    return tenant_data


@app.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: str):
    if tenant_id not in TENANTS_DB:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return TENANTS_DB[tenant_id]


@app.post("/tenants/{tenant_id}/run")
async def run_tenant_graph(tenant_id: str, background_tasks: BackgroundTasks):
    if tenant_id not in TENANTS_DB:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    await sse_manager.broadcast_event(
        tenant_id=tenant_id,
        event_type="node_change",
        data={"node": "ideation", "status": "running", "message": "Iniciando generación de ideas..."},
    )
    TENANTS_DB[tenant_id]["state"]["node"] = "human_approval_idea"
    return {"status": "started", "tenant_id": tenant_id, "current_node": "human_approval_idea"}


@app.post("/tenants/{tenant_id}/ideas/approve")
async def approve_idea(tenant_id: str, payload: dict):
    if tenant_id not in TENANTS_DB:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    status = payload.get("status", "approved")
    TENANTS_DB[tenant_id]["state"]["idea_approval_status"] = status

    if status == "approved":
        TENANTS_DB[tenant_id]["state"]["node"] = "human_approval_publish"
        await sse_manager.broadcast_event(
            tenant_id=tenant_id,
            event_type="node_change",
            data={"node": "scriptwriting", "status": "completed", "message": "Guion generado. Listo para video."},
        )
    else:
        TENANTS_DB[tenant_id]["state"]["node"] = "ideation"

    return {"tenant_id": tenant_id, "idea_approval_status": status, "next_node": TENANTS_DB[tenant_id]["state"]["node"]}


@app.post("/tenants/{tenant_id}/publish/approve")
async def approve_publish(tenant_id: str, payload: dict):
    if tenant_id not in TENANTS_DB:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    status = payload.get("status", "approved")
    TENANTS_DB[tenant_id]["state"]["publish_approval_status"] = status

    if status == "approved":
        TENANTS_DB[tenant_id]["state"]["node"] = "publish"
        TENANTS_DB[tenant_id]["state"]["published_post_id"] = f"ig_post_{uuid.uuid4().hex[:6]}"
        await sse_manager.broadcast_event(
            tenant_id=tenant_id,
            event_type="node_change",
            data={"node": "publish", "status": "completed", "message": "¡Video publicado en Instagram!"},
        )

    return {"tenant_id": tenant_id, "publish_approval_status": status, "published_post_id": TENANTS_DB[tenant_id]["state"].get("published_post_id")}


@app.get("/api/tenants/{tenant_id}/leads")
def get_tenant_leads(tenant_id: str):
    return [lead for lead in LEADS_DB if lead["tenant_id"] == tenant_id]


@app.get("/realtime/sse/{tenant_id}")
async def sse_endpoint(tenant_id: str):
    return StreamingResponse(
        sse_manager.stream_events(tenant_id),
        media_type="text/event-stream",
    )
