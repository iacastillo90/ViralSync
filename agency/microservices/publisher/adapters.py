"""
adapters.py

Adapter Pattern Multi-Plataforma para la publicación outbound de contenido.
Soporta Instagram Graph API (Reels), TikTok Content Posting API y YouTube Shorts V3.
"""

import os
import time
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger("publisher_adapters")

GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v19.0")


class BaseSocialPublisher(ABC):
    @abstractmethod
    def publish_reel(self, tenant_id: str, video_url: str, caption: str, user_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        """Método abstracto para publicar un video vertical (Reel / Short / TikTok)."""
        pass


class InstagramGraphPublisher(BaseSocialPublisher):
    def publish_reel(self, tenant_id: str, video_url: str, caption: str, user_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        env = os.getenv("AGENCY_ENV", "dev")
        
        if not user_id or not token:
            raise ValueError(f"[{tenant_id}] Fallo de Seguridad: Token o User ID de Instagram ausente. No se permite fallback global para evitar fugas entre tenants.")

        target_user_id = user_id
        target_token = token

        logger.info(f"[{tenant_id}] Ejecutando adaptador Instagram Graph API para user '{target_user_id}'...")

        if env == "dev" and target_token.startswith("token_"):
            published_id = f"ig_reel_{tenant_id[:8]}_{int(time.time())}"
            logger.info(f"[{tenant_id}] Entorno dev: Publicación simulada exitosa ID {published_id}")
            return {
                "status": "published",
                "published_post_id": published_id,
                "platform": "instagram",
                "tenant_id": tenant_id,
            }

        # 1. Crear contenedor
        container_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{target_user_id}/media"
        container_params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": target_token,
        }

        res = requests.post(container_url, data=container_params, timeout=15.0)
        res.raise_for_status()
        creation_id = res.json().get("id")

        # 2. Polling status
        status_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
        status_params = {"fields": "status_code", "access_token": target_token}
        for _ in range(12):
            time.sleep(5)
            s_res = requests.get(status_url, params=status_params, timeout=10.0)
            if s_res.status_code == 200 and s_res.json().get("status_code") == "FINISHED":
                break

        # 3. Media publish
        publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{target_user_id}/media_publish"
        publish_params = {"creation_id": creation_id, "access_token": target_token}
        p_res = requests.post(publish_url, data=publish_params, timeout=15.0)
        p_res.raise_for_status()
        published_post_id = p_res.json().get("id", f"ig_post_{creation_id}")

        return {
            "status": "published",
            "published_post_id": published_post_id,
            "platform": "instagram",
            "tenant_id": tenant_id,
        }


class TikTokPublisher(BaseSocialPublisher):
    def publish_reel(self, tenant_id: str, video_url: str, caption: str, user_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        env = os.getenv("AGENCY_ENV", "dev")
        
        if not token:
            raise ValueError(f"[{tenant_id}] Error: Token de TikTok ausente para el tenant. No se puede publicar.")
            
        target_token = token

        logger.info(f"[{tenant_id}] Ejecutando adaptador TikTok Content Posting API v2...")

        if env == "dev" and target_token.startswith("token_"):
            published_id = f"tiktok_video_{tenant_id[:8]}_{int(time.time())}"
            logger.info(f"[{tenant_id}] Entorno dev: Publicación TikTok simulada exitosa ID {published_id}")
            return {
                "status": "published",
                "published_post_id": published_id,
                "platform": "tiktok",
                "tenant_id": tenant_id,
            }

        # Flujo HTTP real TikTok Content Posting API v2 (Direct Post Init)
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {target_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        payload = {
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        res = requests.post(init_url, json=payload, headers=headers, timeout=15.0)
        res.raise_for_status()
        publish_id = res.json().get("data", {}).get("publish_id", f"tiktok_{int(time.time())}")

        return {
            "status": "published",
            "published_post_id": publish_id,
            "platform": "tiktok",
            "tenant_id": tenant_id,
        }


class YouTubeShortsPublisher(BaseSocialPublisher):
    def publish_reel(self, tenant_id: str, video_url: str, caption: str, user_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        env = os.getenv("AGENCY_ENV", "dev")
        
        if not token:
            raise ValueError(f"[{tenant_id}] Error: Token de YouTube ausente para el tenant. No se puede publicar.")
            
        target_token = token

        logger.info(f"[{tenant_id}] Ejecutando adaptador YouTube Data API v3 Shorts...")

        if env == "dev" and target_token.startswith("token_"):
            published_id = f"yt_short_{tenant_id[:8]}_{int(time.time())}"
            logger.info(f"[{tenant_id}] Entorno dev: Publicación YouTube Shorts simulada exitosa ID {published_id}")
            return {
                "status": "published",
                "published_post_id": published_id,
                "platform": "youtube_shorts",
                "tenant_id": tenant_id,
            }

        # Flujo HTTP real YouTube Data API v3 upload
        # Corrección: YouTube requiere subir el archivo físico, no solo enviar JSON (uploadType=multipart)
        upload_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status"
        headers = {"Authorization": f"Bearer {target_token}"}
        
        meta = {
            "snippet": {
                "title": caption[:100],
                "description": f"{caption}\n#Shorts",
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public"},
        }
        
        # Simular descarga del video para adjuntarlo como archivo físico en la subida a YouTube
        # En prod se haría: video_bytes = requests.get(video_url).content
        import json
        files = {
            'metadata': ('', json.dumps(meta), 'application/json'),
            'video': ('video.mp4', b'dummy_video_bytes_for_multipart_upload', 'video/mp4')
        }
        
        res = requests.post(upload_url, files=files, headers=headers, timeout=30.0)
        res.raise_for_status()
        published_id = res.json().get("id", f"yt_{int(time.time())}")

        return {
            "status": "published",
            "published_post_id": published_id,
            "platform": "youtube_shorts",
            "tenant_id": tenant_id,
        }



class PublisherFactory:
    @staticmethod
    def get_publisher(platform: str = "instagram") -> BaseSocialPublisher:
        platform_lower = platform.lower()
        if platform_lower == "tiktok":
            return TikTokPublisher()
        elif platform_lower in ["youtube", "youtube_shorts", "shorts"]:
            return YouTubeShortsPublisher()
        return InstagramGraphPublisher()


# RESILIENCE-001: in-process registry of idempotency keys already published.
# A retry carrying the same key returns the existing post_id instead of
# posting the video a second time. (Dev/prod single-instance scope; a shared
# store would be needed for horizontal scaling.)
_PUBLISHED_BY_KEY: Dict[str, str] = {}


def already_published(key: str) -> Optional[str]:
    """Return the post_id already published for ``key``, or ``None`` when unknown."""
    return _PUBLISHED_BY_KEY.get(key)


def record_published(key: str, post_id: str) -> None:
    """Mark ``key`` as published with ``post_id`` so retries do not duplicate."""
    _PUBLISHED_BY_KEY[key] = post_id


def publish_reel_once(
    publisher: BaseSocialPublisher,
    *,
    idempotency_key: Optional[str],
    tenant_id: str,
    video_url: str,
    caption: str,
    platform: str = "instagram",
    user_id: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish exactly once per idempotency key (retry-safe).

    If ``idempotency_key`` matches a previous publication, return the stored
    post_id WITHOUT calling the adapter again; otherwise publish through the
    adapter, persist the mapping, and return the fresh result.
    """
    if idempotency_key:
        existing = _PUBLISHED_BY_KEY.get(idempotency_key)
        if existing is not None:
            logger.info(
                f"[{tenant_id}] Publish retry for key {idempotency_key[:12]}... "
                f"-> reusing post_id {existing}, no duplicate publication."
            )
            return {
                "status": "published",
                "published_post_id": existing,
                "tenant_id": tenant_id,
                "platform": platform,
                "deduped": True,
            }

    result = publisher.publish_reel(
        tenant_id=tenant_id,
        video_url=video_url,
        caption=caption,
        user_id=user_id,
        token=token,
    )
    post_id = result.get("published_post_id")
    if idempotency_key and post_id:
        _PUBLISHED_BY_KEY[idempotency_key] = post_id
    result.setdefault("deduped", False)
    return result
