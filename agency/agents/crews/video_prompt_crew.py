"""
video_prompt_crew.py

Crew de Prompting Visual y Directiva de Cámara de ViralSync (CrewAI):
Desglosa el guion en 4 bloques en una secuencia de escenas (Storyboard)
con prompts cinematográficos altamente detallados optimizados para modelos
Text-to-Video (Fal.ai Wan2.1, Google Veo, CogVideoX, LTX-Video) en formato vertical 9:16.
"""

import logging
import json
from typing import Dict, Any, List
import agents.llm as llm

logger = logging.getLogger(__name__)


async def run_video_prompt_crew(
    script: Dict[str, Any], idea: Dict[str, Any], product_image_url: str = ""
) -> List[Dict[str, Any]]:
    """
    Desglosa el guion en escenas segundo a segundo con prompts cinematográficos.

    :param script: Guion de 4 bloques (gancho_0_5s, contexto_5_30s, moraleja_30_50s, cta_50_60s, keyword).
    :param idea: Diccionario con la idea aprobada.
    :param product_image_url: URL de la foto del producto guardada en MinIO (Image-to-Video).
    :return: Lista de escenas (Storyboard) con prompts en inglés, marcas de tiempo y estilo de cámara.
    """
    logger.info(f"Ejecutando Crew de Prompting Visual (Image-to-Video active: {bool(product_image_url)})")

    idea_title = idea.get("texto", "Estrategia de Crecimiento")
    niche = idea.get("niche", "B2B Marketing")

    gancho = script.get("gancho_0_5s", "")
    contexto = script.get("contexto_5_30s", "")
    moraleja = script.get("moraleja_30_50s", "")
    cta = script.get("cta_50_60s", "")

    storyboard = []

    # Generación dinámica de prompts cinematográficos vía router LLM compartido
    try:
        system_prompt = (
            "You are an expert AI Video Prompt Engineer and Director of Photography for vertical 9:16 short-form content. "
            "Generate highly detailed, cinematic Text-to-Video / Image-to-Video visual prompts in English for 4 sequential scenes. "
            "Output MUST be strict JSON array with 4 scene objects, without markdown wrapping."
        )

        user_prompt = (
            f"Niche: {niche}\n"
            f"Idea: {idea_title}\n"
            f"Product Image URL: {product_image_url or 'None'}\n"
            f"Scene 1 (0s-5s - Hook): {gancho}\n"
            f"Scene 2 (5s-30s - Context): {contexto}\n"
            f"Scene 3 (30s-50s - Moral/Value): {moraleja}\n"
            f"Scene 4 (50s-60s - CTA): {cta}\n\n"
            "Return a JSON array of 4 objects:\n"
            "[\n"
            "  {\n"
            '    "scene_index": 1,\n'
            '    "timestamp_range": "0s - 5s",\n'
            '    "block_type": "gancho",\n'
            '    "audio_text": "...",\n'
            '    "camera_shot": "Macro Close-Up / Dynamic Push-In",\n'
            '    "visual_mode": "IMAGE_TO_VIDEO or TEXT_TO_VIDEO",\n'
            '    "visual_prompt": "Detailed 9:16 vertical cinematic visual prompt in English..."\n'
            "  },\n"
            "  ...\n"
            "]"
        )

        content = (
            await llm.acomplete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )
        ).strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) == 4:
            for sc in parsed:
                sc["image_url"] = product_image_url if product_image_url else None
            storyboard = parsed
    except Exception as exc:
        logger.warning(f"Router LLM no disponible para video prompting ({exc}). Usando fallback cinematográfico.")

    if not storyboard:
        # Storyboard estructurado de respaldo por marcas de tiempo
        storyboard = [
            {
                "scene_index": 1,
                "timestamp_range": "0s - 5s",
                "block_type": "gancho",
                "audio_text": gancho,
                "camera_shot": "Macro Close-Up / Dynamic Push-In",
                "image_url": product_image_url if product_image_url else None,
                "visual_mode": "IMAGE_TO_VIDEO" if product_image_url else "TEXT_TO_VIDEO",
                "visual_prompt": (
                    f"9:16 vertical video, high resolution 4k cinematic style. "
                    + (f"Using reference product image from {product_image_url}. " if product_image_url else "")
                    + f"Intense close-up of a modern entrepreneur reacting in shock while looking at a futuristic digital dashboard showing declining metrics for {niche}. "
                    f"Dramatic neon-blue and warm lighting, shallow depth of field, 24fps filmic color grading."
                ),
            },
            {
                "scene_index": 2,
                "timestamp_range": "5s - 30s",
                "block_type": "contexto",
                "audio_text": contexto,
                "camera_shot": "Medium Tracking Shot",
                "image_url": product_image_url if product_image_url else None,
                "visual_mode": "IMAGE_TO_VIDEO" if product_image_url else "TEXT_TO_VIDEO",
                "visual_prompt": (
                    f"9:16 vertical video, 4k ultra-detailed. "
                    + (f"Featuring product from {product_image_url} in focus. " if product_image_url else "")
                    + f"Fast-paced montage of a sleek modern glass office building, transitioning to hands typing code and analyzing growth charts on a laptop in {niche}. "
                    f"Professional B2B environment, elegant warm lighting, hyperrealistic, sharp focus."
                ),
            },
            {
                "scene_index": 3,
                "timestamp_range": "30s - 50s",
                "block_type": "moraleja",
                "audio_text": moraleja,
                "camera_shot": "Eye-Level Medium Close-Up",
                "image_url": None,
                "visual_mode": "TEXT_TO_VIDEO",
                "visual_prompt": (
                    f"9:16 vertical video, 4k cinematic portrait. "
                    f"A confident business strategist looking directly into the camera in a warmly lit modern studio with bokeh background. "
                    f"Smooth camera slow zoom-in, natural gestures, premium color tone."
                ),
            },
            {
                "scene_index": 4,
                "timestamp_range": "50s - 60s",
                "block_type": "cta",
                "audio_text": cta,
                "camera_shot": "Low Angle Shot / Text Overlay",
                "image_url": product_image_url if product_image_url else None,
                "visual_mode": "IMAGE_TO_VIDEO" if product_image_url else "TEXT_TO_VIDEO",
                "visual_prompt": (
                    f"9:16 vertical video, high impact 4k motion design. "
                    + (f"Hero shot of product {product_image_url} with glowing text overlay. " if product_image_url else "")
                    + f"Glowing 3D typography of key concepts floating over a stylish dark gradient background with floating sparks and subtle light leaks. "
                    f"Vibrant colors, high contrast, commercial quality."
                ),
            },
        ]

    logger.info(f"Storyboard generado exitosamente con {len(storyboard)} escenas.")
    return storyboard

