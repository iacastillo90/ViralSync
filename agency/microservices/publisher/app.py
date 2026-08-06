"""
app.py

Microservicio Outbound de Publicación de Contenido Multicanal (Instagram Graph API & YouTube).
Procesa la publicación oficial de videos .mp4 almacenados en MinIO hacia redes sociales.
"""

import os
import time
import logging
import requests
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("video_publisher")

app = FastAPI(
    title="ViralSync Outbound Publisher Microservice",
    version="1.0.0",
    description="Microservicio para la publicación oficial de Reels en Instagram Graph API",
)

GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v19.0")
INSTAGRAM_DEFAULT_USER_ID = os.getenv("INSTAGRAM_DEFAULT_USER_ID", "17841400000000000")
INSTAGRAM_GRAPH_ACCESS_TOKEN = os.getenv("INSTAGRAM_GRAPH_ACCESS_TOKEN", "token_instagram_dev")


class PublishRequest(BaseModel):
    tenant_id: str = Field(..., example="tenant-demo-001")
    video_url: str = Field(..., example="http://localhost:9000/viralsync-media/tenant-001/edited_output.mp4")
    caption: str = Field(..., example="🚀 3 Errores al Escalar B2B #Marketing #SaaS")
    instagram_user_id: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None)


class PublishResponse(BaseModel):
    status: str
    published_post_id: str
    tenant_id: str
    platform: str = "instagram"


@app.post("/publish", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_video_endpoint(req: PublishRequest):
    """
    Endpoint principal para publicar Reels oficialmente mediante Instagram Graph API.
    """
    env = os.getenv("AGENCY_ENV", "dev")
    user_id = req.instagram_user_id or INSTAGRAM_DEFAULT_USER_ID
    token = req.access_token or INSTAGRAM_GRAPH_ACCESS_TOKEN

    logger.info(f"[{req.tenant_id}] Iniciando publicación outbound en Instagram para ID '{user_id}'...")

    if env == "dev" or token.startswith("token_") or user_id.startswith("17841400000"):
        # Modo simulación dev seguro sin credenciales reales de Meta
        logger.info(f"[{req.tenant_id}] Entorno dev detectado. Simulando publicación exitosa en Instagram Graph API.")
        published_id = f"ig_reel_{req.tenant_id[:8]}_{int(time.time())}"
        return PublishResponse(
            status="published",
            published_post_id=published_id,
            tenant_id=req.tenant_id,
            platform="instagram",
        )

    # 1. Crear contenedor de Reel en Meta (POST /{ig-user-id}/media)
    container_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{user_id}/media"
    container_params = {
        "media_type": "REELS",
        "video_url": req.video_url,
        "caption": req.caption,
        "access_token": token,
    }

    try:
        res = requests.post(container_url, data=container_params, timeout=15.0)
        res.raise_for_status()
        container_data = res.json()
        creation_id = container_data.get("id")
        logger.info(f"[{req.tenant_id}] Contenedor Reel creado en Meta: ID {creation_id}")

        # 2. Polling hasta que el video sea procesado por Meta
        status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
        status_params = {"fields": "status_code", "access_token": token}
        
        for _ in range(12):
            time.sleep(5)
            s_res = requests.get(status_url, params=status_params, timeout=10.0)
            if s_res.status_code == 200 and s_res.json().get("status_code") == "FINISHED":
                logger.info(f"[{req.tenant_id}] Procesamiento de video en Meta finalizado (FINISHED).")
                break

        # 3. Publicar oficialmente (POST /{ig-user-id}/media_publish)
        publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{user_id}/media_publish"
        publish_params = {"creation_id": creation_id, "access_token": token}

        p_res = requests.post(publish_url, data=publish_params, timeout=15.0)
        p_res.raise_for_status()
        published_post_id = p_res.json().get("id", f"ig_post_{creation_id}")

        logger.info(f"[{req.tenant_id}] Reel publicado oficialmente en Instagram: ID {published_post_id}")
        return PublishResponse(
            status="published",
            published_post_id=published_post_id,
            tenant_id=req.tenant_id,
            platform="instagram",
        )

    except Exception as exc:
        logger.error(f"Error durante la publicación en Instagram Graph API: {exc}")
        raise HTTPException(status_code=500, detail=f"Error en publicación oficial Instagram: {str(exc)}")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "video_publisher"}
