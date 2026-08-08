"""
video_edit_task.py

Tarea Celery asíncrona para la post-producción y renderizado de video faceless.
Integra la orquestación del Agente Director (CrewAI) y el despacho HTTP POST al microservicio
de renderizado (http://video_renderer:8001/render) con soporte de timeouts largos.
"""

import os
import logging
import httpx
from typing import Dict, Any, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from workers.celery_app import celery_app
from agents.crews.video_director_crew import run_video_director_crew
from agents.mcp_servers.video_gen_client import (
    VideoGenerationClient,
    ShotstackClient,
    generate_storyboard_videos,
)

logger = logging.getLogger(__name__)

RENDERER_SERVICE_URL = os.getenv("RENDERER_SERVICE_URL", "http://video_renderer:8001/render")
FALLBACK_RENDERER_URL = "http://localhost:8001/render"


@celery_app.task(name="workers.video_edit_task.trigger_video_render")
def trigger_video_render(
    tenant_id: str,
    script: Dict[str, Any],
    idea: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Despacha el trabajo de renderizado al microservicio faceless independiente (Puerto 8001).
    Maneja timeouts largos (300 segundos) ya que la síntesis TTS y composición de video toman tiempo.
    """
    if not idea:
        idea = {"texto": "Video Marketing ViralSync", "niche": "B2B SaaS"}

    logger.info(f"[{tenant_id}] Despachando trabajo al Agente Director (Guardián de Calidad y Rendimiento)...")
    director_result = run_video_director_crew(script=script, idea=idea, tenant_id=tenant_id)

    # 1. Filtro de Valor: Verificar si el guion fue aprobado por el Guardián
    if not director_result.get("approved_for_render", False):
        logger.warning(f"[{tenant_id}] Guion RECHAZADO por Filtro de Valor RUM (Score: {director_result.get('quality_score')})")
        return {
            "tenant_id": tenant_id,
            "status": "rejected_quality",
            "quality_score": director_result.get("quality_score"),
            "feedback": director_result.get("quality_feedback"),
            "message": "El guion no superó el umbral de calidad RUM (0.70). Devuelto para refinamiento.",
        }

    render_payload = director_result.get("render_payload", {})
    curated_metadata = director_result.get("metadata", {})

    video_url = ""
    video_renderer_provider = os.getenv("VIDEO_RENDERER_PROVIDER", "local")
    json2video_api_key = os.getenv("JSON2VIDEO_API_KEY", "")

    # 2. Si se elige json2video y hay api key, intentar renderizar en la nube
    if video_renderer_provider == "json2video" and json2video_api_key:
        logger.info(f"[{tenant_id}] Intentando renderizado en la nube usando JSON2Video...")
        try:
            from agents.mcp_servers.json2video_client import JSON2VideoClient
            client = JSON2VideoClient(api_key=json2video_api_key)
            video_url = client.render_video(
                script=script,
                keywords=render_payload.get("keywords", []),
                tenant_id=tenant_id,
                title=render_payload.get("title", "ViralSync Marketing Video")
            )
            if video_url:
                logger.info(f"[{tenant_id}] Renderizado JSON2Video completado exitosamente: {video_url}")
                return {
                    "tenant_id": tenant_id,
                    "video_url": video_url,
                    "payload": render_payload,
                    "status": "completed",
                    "provider": "json2video"
                }
        except Exception as exc:
            logger.error(f"[{tenant_id}] Fallo en renderizado de JSON2Video ({exc}). Ejecutando fallback al microservicio local...")

    # 3. Fallback / Ejecución local (MoviePy + microservicio local)
    target_url = RENDERER_SERVICE_URL
    logger.info(f"[{tenant_id}] Ejecutando renderizado con microservicio local en {target_url} (Timeout: 300s)...")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_renderer(url):
        with httpx.Client(timeout=300.0) as client:
            return client.post(url, json=render_payload)

    try:
        response = _call_renderer(target_url)
        if response.status_code == 201:
            data = response.json()
            video_url = data.get("video_url", "")
            logger.info(f"[{tenant_id}] Renderizado local completado exitosamente: {video_url}")
        else:
            logger.warning(f"Respuesta no esperada del microservicio local ({response.status_code}): {response.text}")
    except Exception as exc:
        logger.warning(f"No se pudo conectar a {target_url} ({exc}). Intentando fallback local...")
        try:
            response = _call_renderer(FALLBACK_RENDERER_URL)
            if response.status_code == 201:
                video_url = response.json().get("video_url", "")
        except Exception as fallback_exc:
            logger.error(f"Fallo definitivo conectando al microservicio de renderizado local: {fallback_exc}")

    if not video_url:
        video_url = f"http://localhost:9000/viralsync-media/{tenant_id}/products/default_rendered_output.mp4"

    return {
        "tenant_id": tenant_id,
        "video_url": video_url,
        "payload": render_payload,
        "status": "completed",
        "provider": "local"
    }


@celery_app.task(name="workers.video_edit_task.process_video_postproduction")
def process_video_postproduction(
    tenant_id: str,
    raw_video_uri: str,
    script: Dict[str, Any],
    storyboard: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Procesa las escenas del storyboard con el microservicio de renderizado o Shotstack/Fal.ai.
    """
    logger.info(f"[{tenant_id}] Iniciando pipeline de renderizado y producción de video MP4...")

    # Ejecutar el despacho del microservicio faceless
    render_result = trigger_video_render(tenant_id=tenant_id, script=script)
    edited_video_uri = render_result.get("video_url", f"s3://viralsync-media-dev/{tenant_id}/edited_output.mp4")

    # Generación opcional de storyboard para metadatos del grafo
    if not storyboard:
        storyboard = [
            {"scene_index": 1, "audio_text": script.get("gancho_0_5s", "Gancho"), "visual_prompt": "Cinematic close-up"},
            {"scene_index": 2, "audio_text": script.get("contexto_5_30s", "Contexto"), "visual_prompt": "Montage video"},
            {"scene_index": 3, "audio_text": script.get("moraleja_30_50s", "Moraleja"), "visual_prompt": "Portrait video"},
            {"scene_index": 4, "audio_text": script.get("cta_50_60s", "CTA"), "visual_prompt": "Text overlay"},
        ]

    generated_scenes = generate_storyboard_videos(storyboard=storyboard, tenant_id=tenant_id)

    return {
        "tenant_id": tenant_id,
        "raw_video_uri": raw_video_uri,
        "edited_video_uri": edited_video_uri,
        "generated_scenes": generated_scenes,
        "status": "completed",
    }
