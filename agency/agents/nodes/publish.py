"""
Nodo de publicación (AGENTS.md sección 8: "browser-use nunca contra Instagram").

Usa exclusivamente la Instagram Graph API oficial con el token del tenant
(INSTAGRAM_GRAPH_API_TOKEN, por tenant, nunca compartido). El caption
incluye siempre la palabra clave única de la campaña (AGENTS.md 7.9,
paso 1) para que el webhook inbound pueda atribuir leads a este video_id.
"""

import httpx


GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


def run(state: dict) -> dict:
    tenant_id = state["tenant_id"]
    edited_uri = state["edited_video_uri"]
    script = state["script"]
    token = state["_secrets"]["instagram_graph_api_token"]  # inyectado por el backend, nunca hardcodeado
    ig_user_id = state["_secrets"]["instagram_business_account_id"]

    caption = script["cta_50_60s"]

    with httpx.Client(timeout=60) as client:
        create = client.post(
            f"{GRAPH_API_BASE}/{ig_user_id}/media",
            params={
                "video_url": edited_uri,
                "caption": caption,
                "media_type": "REELS",
                "access_token": token,
            },
        )
        create.raise_for_status()
        creation_id = create.json()["id"]

        publish = client.post(
            f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
            params={"creation_id": creation_id, "access_token": token},
        )
        publish.raise_for_status()
        post_id = publish.json()["id"]

    return {"published_post_id": post_id}
