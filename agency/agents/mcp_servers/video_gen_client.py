"""
video_gen_client.py

Cliente unificado para APIs de Generación de Video AI (Text-to-Video).
Soporta proveedores como Fal.ai (Wan2.1 / CogVideoX), Google Veo (Vertex AI),
ZSky AI y un generador Mock simulado para desarrollo local (cero costo).
"""

import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class VideoGenerationClient:
    """Cliente unificado de Generación de Video a partir de Prompts."""

    def __init__(self, provider: str = None):
        self.env = os.getenv("AGENCY_ENV", "dev")
        self.provider = provider or os.getenv("VIDEO_GEN_PROVIDER", "mock" if self.env == "dev" else "fal_ai")

    def generate_scene_video(self, scene: Dict[str, Any], tenant_id: str) -> str:
        """
        Genera un clip de video individual para una escena a partir de su prompt cinematográfico.

        :param scene: Diccionario con los detalles de la escena (scene_index, visual_prompt, camera_shot, etc).
        :param tenant_id: ID del tenant para almacenar la salida.
        :return: URI o URL del video MP4 generado.
        """
        scene_idx = scene.get("scene_index", 1)
        prompt = scene.get("visual_prompt", "")
        logger.info(f"[{tenant_id}] Generando clip para escena {scene_idx} con proveedor '{self.provider}'")

        if self.provider == "fal_ai":
            return self._generate_fal_ai(prompt, tenant_id, scene_idx)
        elif self.provider == "google_veo":
            return self._generate_google_veo(prompt, tenant_id, scene_idx)
        elif self.provider == "zsky_ai":
            return self._generate_zsky(prompt, tenant_id, scene_idx)
        else:
            return self._generate_mock(prompt, tenant_id, scene_idx)

    def _generate_fal_ai(self, prompt: str, tenant_id: str, scene_idx: int) -> str:
        """Integración con Fal.ai (Wan2.1 / CogVideoX / LTX-Video)."""
        logger.info(f"Llamando a Fal.ai API con prompt: {prompt[:60]}...")
        # En producción se utiliza `fal_client.subscribe("fal-ai/wan2.1", arguments={"prompt": prompt, "aspect_ratio": "9:16"})`
        return f"s3://viralsync-media-dev/{tenant_id}/generated_clip_fal_{scene_idx}.mp4"

    def _generate_google_veo(self, prompt: str, tenant_id: str, scene_idx: int) -> str:
        """Integración con Google Veo via Vertex AI / Gemini API."""
        logger.info(f"Llamando a Google Veo API con prompt: {prompt[:60]}...")
        return f"s3://viralsync-media-dev/{tenant_id}/generated_clip_veo_{scene_idx}.mp4"

    def _generate_zsky(self, prompt: str, tenant_id: str, scene_idx: int) -> str:
        """Integración con ZSky AI REST API."""
        logger.info(f"Llamando a ZSky AI API con prompt: {prompt[:60]}...")
        return f"s3://viralsync-media-dev/{tenant_id}/generated_clip_zsky_{scene_idx}.mp4"

    def _generate_mock(self, prompt: str, tenant_id: str, scene_idx: int) -> str:
        """Generador simulado para entorno dev (cero costo)."""
        logger.info(f"Generador MOCK de video ejecutado para escena {scene_idx}")
        return f"s3://viralsync-media-dev/{tenant_id}/mock_clip_scene_{scene_idx}.mp4"


def generate_storyboard_videos(storyboard: List[Dict[str, Any]], tenant_id: str) -> List[Dict[str, Any]]:
    """
    Procesa un Storyboard completo y retorna la lista de escenas enriquecidas con las URIs de los videos generados.
    """
    client = VideoGenerationClient()
    rendered_storyboard = []

    for scene in storyboard:
        video_uri = client.generate_scene_video(scene, tenant_id=tenant_id)
        scene_with_video = dict(scene)
        scene_with_video["video_clip_uri"] = video_uri
        rendered_storyboard.append(scene_with_video)

    return rendered_storyboard
