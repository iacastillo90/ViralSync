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
from agents.crews.prompt_context import build_trend_section, resolve_rum_threshold
import agents.llm as llm

logger = logging.getLogger(__name__)


async def run_video_prompt_crew(
    script: Dict[str, Any], idea: Dict[str, Any], product_image_url: str = "", target_duration: float = 30.0
) -> List[Dict[str, Any]]:
    """
    Desglosa el guion en escenas exactas de 5 segundos con prompts cinematográficos.
    Para 15s -> 3 escenas de 5s
    Para 30s -> 6 escenas de 5s
    Para 45s -> 9 escenas de 5s
    Para 60s -> 12 escenas de 5s

    :param script: Guion de 4 bloques (gancho_0_5s, contexto_5_30s, moraleja_30_50s, cta_50_60s, keyword).
    :param idea: Diccionario con la idea aprobada.
    :param product_image_url: URL de la foto del producto guardada en MinIO.
    :param target_duration: Duración objetivo en segundos (15.0, 30.0, 45.0, 60.0).
    :return: Lista de escenas (Storyboard) con 1 prompt de 5s por cada intervalo de 5 segundos.
    """
    duration = float(script.get("target_duration") or target_duration or 30.0)
    num_scenes = max(3, int(round(duration / 5.0)))
    logger.info(f"Ejecutando Crew de Prompting Visual (Duración: {duration}s -> {num_scenes} escenas de 5s)")

    idea_title = idea.get("texto", "Estrategia de Crecimiento")
    niche = idea.get("niche", "B2B Marketing")

    gancho = script.get("gancho_0_5s", "")
    contexto = script.get("contexto_5_30s", "")
    moraleja = script.get("moraleja_30_50s", "")
    cta = script.get("cta_50_60s", "")

    full_script_text = f"{gancho} {contexto} {moraleja} {cta}".strip()

    storyboard = []

    try:
        rum_threshold = resolve_rum_threshold(niche)
        trend_section = build_trend_section(niche)
        trend_line = (
            f"Trending topics ({niche}):\n{trend_section}\n"
            if trend_section
            else ""
        )

        system_prompt = (
            "You are an award-winning Director of Photography and AI Video Prompt Engineer for vertical 9:16 short-form "
            "content (Instagram Reels / TikTok / YouTube Shorts). Your prompts must read like a professional film set "
            "briefing, not a hobbyist description. "
            "For every scene you MUST specify, in the visual_prompt, the following craft layers, adapting them to the scene:\n"
            "1. LENS & OPTICS: concrete focal length (e.g. 24mm, 35mm, 50mm, 85mm, 100mm macro) and aperture (e.g. f/1.4, "
            "f/2.8) with the resulting look (shallow depth of field, creamy bokeh, anamorphic flaring, distortion).\n"
            "2. CAMERA & MOTION: exact move (e.g. slow dolly-in, gimbal tracking, crane rise, whip pan, orbital rotation, "
            "rack focus pull, handheld micro-jitter for energy) and frame rate feel (24fps cinematic or 30fps punchy).\n"
            "3. LIGHTING & MOOD: motivated light design (e.g. Rembrandt key with softbox, golden hour backlight, practical "
            "neon rim light, high-key product beauty, dramatic chiaroscuro, volumetric haze).\n"
            "4. COMPOSITION & BLOCKING: framing rule (rule of thirds, centered symmetry, leading lines, negative space), "
            "camera height, subject placement and depth staging (foreground/midground/background).\n"
            "5. COLOR & GRADE: palette and finish (teal-and-orange, warm skin-tone falloff, muted loyal-to-brand colors, "
            "film emulation with halation and subtle grain, high contrast punch).\n"
            "6. PRODUCTION QUALITY: photorealistic, 4K/8K detail, clean motion, consistent subject identity across scenes, "
            "no warping, no morphing artifacts.\n"
            "Also include the model-friendly cues in English (camera_shot and visual_prompt), and the subject/scene rhythm "
            "so the 5-second shots cut together as one coherent edit (same product, consistent brand colors, continuous "
            "action across scenes).\n"
            f"Generate exactly {num_scenes} sequential 5-second scene prompts in English for a {duration}-second short video. "
            "CRITICAL: The 'audio_text' field MUST ALWAYS REMAIN EXACTLY IN SPANISH (Español Latino) from the input script. "
            "DO NOT translate 'audio_text' to English! ONLY 'visual_prompt' and 'camera_shot' should be in English. "
            f"Output MUST be a strict JSON array with exactly {num_scenes} scene objects, without markdown wrapping."
        )

        user_prompt = (
            f"Niche: {niche}\n"
            f"Target Duration: {duration} seconds ({num_scenes} scenes of 5s each)\n"
            f"Idea: {idea_title}\n"
            f"Product Image URL: {product_image_url or 'None'}\n"
            f"Full Script (Spanish): {full_script_text}\n\n"
            "Direct the 5-second scenes so they read as ONE professionally produced vertical spot: consistent product, "
            "consistent color palette, continuous motion/blocking across scene boundaries (180-degree rule respected, "
            "no disorienting jumps).\n\n"
            "Use the following craft template as reference quality, adapting lens/mood/grade to each block:\n"
            "  visual_prompt: \"85mm f/1.8, shallow depth of field with creamy bokeh, slow dolly-in push on the subject, "
            "Rembrandt key lighting with softbox plus warm practical rim light, rule-of-thirds composition, subject staged "
            "mid-frame with foreground haze, teal-and-orange film grade with subtle halation and gentle grain, photorealistic, "
            "8K detail, consistent skin textures, 24fps cinematic motion, no warping, 5-second clip\"\n\n"
            "Return a JSON array of exactly " + str(num_scenes) + " objects:\n"
            "[\n"
            "  {\n"
            '    "scene_index": 1,\n'
            '    "timestamp_range": "0s - 5s",\n'
            '    "block_type": "gancho",\n'
            '    "audio_text": "Spanish spoken audio segment for this 5s shot...",\n'
            '    "camera_shot": "85mm Close-Up, f/1.8, slow dolly-in (Rembrandt key)",\n'
            '    "visual_mode": "TEXT_TO_VIDEO",\n'
            '    "visual_prompt": "Detailed 9:16 vertical cinematic visual prompt in English following the craft template..."\n'
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
                max_tokens=2500,
            )
        ).strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) >= num_scenes:
            for sc in parsed:
                sc["image_url"] = product_image_url if product_image_url else None
            storyboard = parsed[:num_scenes]
    except Exception as exc:
        logger.warning(f"Router LLM no disponible para video prompting ({exc}). Generando {num_scenes} escenas de 5s en fallback.")

    if not storyboard:
        # Fallback dinámico de N escenas de 5s
        blocks = [
            ("gancho", gancho or "Gancho inicial"),
            ("contexto_1", contexto[:len(contexto)//2] if contexto else "Contexto del problema"),
            ("contexto_2", contexto[len(contexto)//2:] if contexto else "Solución propuesta"),
            ("moraleja_1", moraleja[:len(moraleja)//2] if moraleja else "Demostración de valor"),
            ("moraleja_2", moraleja[len(moraleja)//2:] if moraleja else "Resultado y beneficio"),
            ("cta", cta or "Llamado a la acción final"),
        ]

        shots = [
            "85mm f/1.8 Close-Up, shallow depth of field, slow dolly-in push, Rembrandt key with softbox",
            "35mm f/2.8 Medium Shot, smooth gimbal pan, golden-hour backlight rim, leading lines",
            "50mm f/1.4 Over-Shoulder, rack focus pull, neutral practical light, layered depth",
            "24mm f/2.8 Low-Angle Dynamic Tracking, dramatic upward tilt, strong foreground parallax",
            "100mm macro Product Orbit, ring-light beauty sweep, crisp textures, seamless rotation",
            "40mm f/2 Center Framed, slow zoom-out reveal, soft volumetric haze, high-key product glow",
        ]

        for i in range(num_scenes):
            start_s = i * 5
            end_s = (i + 1) * 5
            b_type, a_txt = blocks[i % len(blocks)]
            c_shot = shots[i % len(shots)]
            storyboard.append({
                "scene_index": i + 1,
                "timestamp_range": f"{start_s}s - {end_s}s",
                "block_type": b_type,
                "audio_text": a_txt,
                "camera_shot": c_shot,
                "image_url": product_image_url if product_image_url else None,
                "visual_mode": "TEXT_TO_VIDEO",
                "visual_prompt": (
                    f"9:16 vertical cinematic production shot, {c_shot}. "
                    f"Motivated lighting with key/rim separation, rule-of-thirds composition, "
                    "clean color grade with film emulation (subtle grain and halation), "
                    "photorealistic 8K detail, consistent subject identity, 24fps cinematic motion, "
                    f"5-second clip showing: {a_txt[:40]}"
                ),
            })

    logger.info(f"Storyboard generado exitosamente con {len(storyboard)} escenas.")
    return storyboard
