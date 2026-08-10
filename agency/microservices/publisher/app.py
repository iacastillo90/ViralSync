"""
app.py

Microservicio Outbound de Publicación de Contenido Multicanal (Instagram Graph API, TikTok & YouTube Shorts).
"""

import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from adapters import PublisherFactory, publish_reel_once

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("video_publisher")

app = FastAPI(
    title="ViralSync Outbound Publisher Microservice",
    version="1.0.0",
    description="Microservicio multi-plataforma para publicar Reels y Shorts usando Adapter Pattern",
)


class PublishRequest(BaseModel):
    tenant_id: str = Field(..., example="tenant-demo-001")
    video_url: str = Field(..., example="http://localhost:9000/viralsync-media/tenant-001/edited_output.mp4")
    caption: str = Field(..., example="🚀 3 Errores al Escalar B2B #Marketing #SaaS")
    platform: Optional[str] = Field(default="instagram", example="instagram")
    instagram_user_id: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Stable key so retries of the same publish are deduped (RESILIENCE-001).",
    )


class PublishResponse(BaseModel):
    status: str
    published_post_id: str
    tenant_id: str
    platform: str


@app.post("/publish", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_video_endpoint(req: PublishRequest):
    """
    Endpoint principal para publicar Reels/Shorts multicanal usando Adapter Pattern.
    """
    logger.info(f"[{req.tenant_id}] Solicitud de publicación recibida para plataforma '{req.platform}'")
    publisher = PublisherFactory.get_publisher(req.platform)

    try:
        result = publish_reel_once(
            publisher,
            idempotency_key=req.idempotency_key,
            platform=req.platform or "instagram",
            tenant_id=req.tenant_id,
            video_url=req.video_url,
            caption=req.caption,
            user_id=req.instagram_user_id,
            token=req.access_token,
        )
        if result.get("deduped"):
            logger.info(
                f"[{req.tenant_id}] Idempotency key {req.idempotency_key[:12]}... "
                "replayed: returning existing post without republishing."
            )
        return PublishResponse(
            status=result["status"],
            published_post_id=result["published_post_id"],
            tenant_id=result["tenant_id"],
            platform=result["platform"],
        )
    except Exception as exc:
        logger.error(f"Error en publicación outbound ({req.platform}): {exc}")
        raise HTTPException(status_code=500, detail=f"Error en publicación {req.platform}: {str(exc)}")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "video_publisher"}
