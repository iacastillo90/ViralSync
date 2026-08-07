import logging
from typing import Dict, Any
from microservices.publisher.adapters import PublisherFactory

logger = logging.getLogger(__name__)


def node_publish(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo que efectúa la publicación final en redes sociales vía Publisher Adapter."""
    tenant_id = state.get("tenant_id", "default_tenant")
    edited_uri = state.get("edited_video_uri", f"s3://viralsync-media-dev/{tenant_id}/edited_output.mp4")
    script = state.get("script", {})
    caption = f"{script.get('gancho_0_5s', '')}\n\n{script.get('cta_50_60s', '')}"
    platform = state.get("target_platform", "instagram")

    # Extraer credenciales OAuth desde el estado del grafo.
    # El estado las recibe del endpoint /graph/run → vienen del frontend (sesión del usuario).
    user_id = state.get("ig_user_id")
    token = state.get("ig_access_token")
    if platform == "tiktok":
        token = state.get("tiktok_access_token")
    elif platform == "youtube_shorts":
        token = state.get("youtube_access_token")

    logger.info(f"[{tenant_id}] Ejecutando nodo 'publish' en plataforma '{platform}' para video '{edited_uri}'")

    publisher = PublisherFactory.get_publisher(platform=platform)
    publish_result = publisher.publish_reel(
        tenant_id=tenant_id,
        video_url=edited_uri,
        caption=caption,
        user_id=user_id,
        token=token,
    )

    post_id = publish_result.get("published_post_id", f"post_{tenant_id[:8]}")

    logs = state.get("logs", [])
    logs.append(f"[publish] Video publicado en {platform.capitalize()} con Post ID '{post_id}'")

    return {
        "published_post_id": post_id,
        "logs": logs,
    }

