"""
script_exporter.py

Servicio para empacar y exportar el paquete creativo completo de un guión en un archivo ZIP.

Archivos contenidos en el paquete ZIP:
 - `guion.txt`: Los 4 bloques narrativos formateados para lectura rápida.
 - `guion.json`: Representación JSON estructurada del guión.
 - `prompts_escenas.json`: Desglose de prompts visuales para generación de video IA por escenas.
 - `descripcion_post.txt`: Copy promocional para redes sociales (Instagram Reels/TikTok) con hashtags.
 - `video.mp4`: Si la pieza fue renderizada y se encuentra disponible localmente.
"""

import io
import os
import json
import zipfile
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def build_scene_prompts(script: Dict[str, Any]) -> list:
    """Genera 6 escenas de 5s a partir de los 4 bloques del guión."""
    gancho = script.get("gancho_0_5s", "")
    contexto = script.get("contexto_5_30s", "")
    moraleja = script.get("moraleja_30_50s", "")
    cta = script.get("cta_50_60s", "")
    kw = script.get("keyword", "VIRAL")

    return [
        {"scene": 1, "time": "0-5s", "block": "Gancho", "prompt": f"High engagement visual: {gancho}, 9:16 vertical, cinematic lighting, 4k ultra detailed"},
        {"scene": 2, "time": "5-15s", "block": "Contexto Pt 1", "prompt": f"Dynamic scene showing the problem: {contexto[:100]}, dramatic color grade"},
        {"scene": 3, "time": "15-30s", "block": "Contexto Pt 2", "prompt": f"Continuation of context: {contexto[100:200]}, fast cuts, professional look"},
        {"scene": 4, "time": "30-40s", "block": "Moraleja Pt 1", "prompt": f"Solution moment: {moraleja[:100]}, bright uplifting lighting"},
        {"scene": 5, "time": "40-50s", "block": "Moraleja Pt 2", "prompt": f"Key takeaway: {moraleja[100:200]}, high contrast, crisp detail"},
        {"scene": 6, "time": "50-60s", "block": "CTA", "prompt": f"Call to action screen: Comment '{kw}' to get full access, sleek text overlay"},
    ]


def generate_post_caption(script: Dict[str, Any]) -> str:
    """Genera la descripción para la publicación en Instagram/TikTok."""
    gancho = script.get("gancho_0_5s", "")
    contexto = script.get("contexto_5_30s", "")
    moraleja = script.get("moraleja_30_50s", "")
    cta = script.get("cta_50_60s", "")
    kw = script.get("keyword", "SOLICITUD")

    return (
        f"{gancho}\n\n"
        f"💡 {contexto}\n\n"
        f"✨ {moraleja}\n\n"
        f"👇 ¿Quieres saber más?\n"
        f"Comenta '{kw}' en este post y te enviamos toda la información por mensaje directo.\n\n"
        f"#ViralSync #{kw.lower()} #MarketingDigital #ReelsVirales #ContenidoIA"
    )


def create_script_export_zip(
    script: Dict[str, Any],
    video_bytes: Optional[bytes] = None,
    video_filename: str = "video.mp4",
) -> bytes:
    """
    Genera el archivo ZIP en memoria conteniendo todos los componentes del paquete creativo.
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. guion.txt
        txt_content = (
            f"=== GUION VIRAL 4 BLOQUES ===\n"
            f"ID: {script.get('id', 'N/A')}\n"
            f"Palabra Clave CTA: {script.get('keyword', 'N/A')}\n"
            f"Score Viral: {script.get('trend_score', 'N/A')}/100\n\n"
            f"🪝 BLOQUE 1 - GANCHO VIRAL (0-5s):\n{script.get('gancho_0_5s', '')}\n\n"
            f"💡 BLOQUE 2 - CONTEXTO & DESARROLLO (5-30s):\n{script.get('contexto_5_30s', '')}\n\n"
            f"✨ BLOQUE 3 - MORALEJA / SOLUCIÓN (30-50s):\n{script.get('moraleja_30_50s', '')}\n\n"
            f"📣 BLOQUE 4 - LLAMADO A LA ACCIÓN (50-60s):\n{script.get('cta_50_60s', '')}\n"
        )
        zf.writestr("guion.txt", txt_content)

        # 2. guion.json
        zf.writestr("guion.json", json.dumps(script, indent=2, ensure_ascii=False))

        # 3. prompts_escenas.json
        prompts = build_scene_prompts(script)
        zf.writestr("prompts_escenas.json", json.dumps(prompts, indent=2, ensure_ascii=False))

        # 4. descripcion_post.txt
        caption = generate_post_caption(script)
        zf.writestr("descripcion_post.txt", caption)

        # 5. video.mp4 (opcional si existe el binario)
        if video_bytes:
            zf.writestr(video_filename, video_bytes)

    buf.seek(0)
    return buf.getvalue()
