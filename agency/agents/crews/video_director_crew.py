"""
video_director_crew.py

Crew Director de Video de ViralSync (CrewAI):
Actúa como Guardián de Calidad y Rendimiento Final:
1. Filtro de Valor (Impacto RUM): Evalúa retención y densidad de valor antes de autorizar renderizado.
2. Filtro de Hardware: Limita la duración a 45 segundos y fuerza clips ligeros (720p/1080p).
3. Curaduría de Metadatos: Redacta títulos persuasivos, descripciones empáticas y hashtags de nicho.
"""

import logging
import re
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

QUALITY_SCORE_THRESHOLD = 0.70
MAX_VIDEO_DURATION_SECONDS = 45


def evaluate_script_quality(script: Dict[str, Any], idea: Dict[str, Any]) -> Tuple[float, bool, List[str]]:
    """
    Filtro de Valor: Evalúa si el guion resuelve un problema real y garantiza retención.
    
    :param script: Guion de 4 bloques.
    :param idea: Idea de contenido.
    :return: Tupla (quality_score, approved_for_render, feedback_list).
    """
    feedback = []
    score = 0.0

    gancho = script.get("gancho_0_5s", "").strip()
    contexto = script.get("contexto_5_30s", "").strip()
    moraleja = script.get("moraleja_30_50s", "").strip()
    cta = script.get("cta_50_60s", "").strip()

    # 1. Evaluación del Gancho (<5s): Debe captar atención con impacto
    if len(gancho) >= 15:
        score += 0.25
    else:
        feedback.append("El gancho de 0-5s es demasiado corto o carece de fuerza inicial.")

    # 2. Evaluación del Contexto (5-30s): Debe aportar valor real, no solo clickbait
    if len(contexto) >= 40:
        score += 0.30
    else:
        feedback.append("El bloque de contexto requiere mayor densidad de información educativa.")

    # 3. Evaluación de la Moraleja/Demostración (30-50s)
    if len(moraleja) >= 25:
        score += 0.25
    else:
        feedback.append("La moraleja o solución práctica necesita una conclusión más clara.")

    # 4. Evaluación de la Llamada a la Acción (CTA 50-60s) y Palabra Clave
    if len(cta) >= 10 and script.get("keyword"):
        score += 0.20
    else:
        feedback.append("Falta una palabra clave clara de atribución en el CTA.")

    approved = score >= QUALITY_SCORE_THRESHOLD
    logger.info(f"Evaluación del Filtro de Valor: Score={score:.2f} | Aprobado={approved}")
    return round(score, 2), approved, feedback


def curate_video_metadata(script: Dict[str, Any], idea: Dict[str, Any]) -> Dict[str, Any]:
    """
    Curaduría de Metadatos: Genera título persuasivo, descripción empática y hashtags de nicho.
    """
    base_title = idea.get("texto", "Estrategia de Crecimiento")
    niche = idea.get("niche", "Marketing SaaS")
    keyword = script.get("keyword", "CONSULTA")

    # Título humanizado de alto impacto
    final_title = f"🚀 {base_title} | Caso Práctico 2026"

    # Descripción con gancho y llamado a la acción
    gancho = script.get("gancho_0_5s", base_title)
    description = (
        f"{gancho}\n\n"
        f"💡 En este Reel analizamos paso a paso cómo optimizar tu estrategia en {niche}.\n"
        f"📩 Comenta la palabra '{keyword}' abajo y te enviamos el desglose estratégico privado por DM."
    )

    # Hashtags curados por nicho
    niche_tag = niche.lower().replace(" ", "").replace("&", "")
    hashtags = [
        f"#{niche_tag}",
        "#ViralSync",
        "#MarketingDigital",
        "#GrowthHacking",
        "#InteligenciaArtificial",
    ]

    return {
        "final_title": final_title,
        "description": description,
        "hashtags": hashtags,
        "full_caption": f"{description}\n\n" + " ".join(hashtags),
    }


def extract_keywords_from_script(script_text: str, idea_title: str) -> List[str]:
    """Extrae palabras clave visuales precisas para clips ligeros (720p)."""
    base_terms = ["business", "technology", "office", "success", "entrepreneur"]
    title_words = [w.lower() for w in re.findall(r"\b\w{4,}\b", idea_title)]
    keywords = list(dict.fromkeys(title_words + base_terms))[:4]
    return keywords


def run_video_director_crew(
    script: Dict[str, Any], idea: Dict[str, Any], tenant_id: str = "default_tenant"
) -> Dict[str, Any]:
    """
    Ejecuta el Agente Director como Guardián de Calidad y Rendimiento Final.

    :param script: Guion de 4 bloques.
    :param idea: Idea aprobada RUM.
    :param tenant_id: ID del tenant.
    :return: Diccionario con el payload de renderizado y la evaluación del Guardián.
    """
    logger.info(f"[{tenant_id}] Ejecutando Agente Director (Guardián de Calidad & Rendimiento)")

    # 1. Filtro de Valor (Evaluación de Impacto)
    quality_score, approved_for_render, feedback = evaluate_script_quality(script, idea)

    # 2. Curaduría de Metadatos
    metadata = curate_video_metadata(script, idea)

    # 3. Filtro de Hardware (Restricciones Quirúrgicas: Máx 45s, Clips 720p)
    gancho = script.get("gancho_0_5s", "")
    contexto = script.get("contexto_5_30s", "")
    moraleja = script.get("moraleja_30_50s", "")
    cta = script.get("cta_50_60s", "")

    full_script_text = f"{gancho} {contexto} {moraleja} {cta}".strip()
    # Truncar texto si excede aproximadamente 45 segundos de narración (~110 palabras)
    words = full_script_text.split()
    if len(words) > 110:
        full_script_text = " ".join(words[:110]) + "."
        logger.info("Filtro de Hardware: Texto ajustado al límite estricto de 45s.")

    keywords = extract_keywords_from_script(full_script_text, metadata["final_title"])

    render_payload = {
        "title": metadata["final_title"],
        "script_text": full_script_text,
        "keywords": keywords,
        "tenant_id": tenant_id,
        "max_duration_seconds": MAX_VIDEO_DURATION_SECONDS,
        "requested_resolution": "720p",
    }

    return {
        "tenant_id": tenant_id,
        "quality_score": quality_score,
        "approved_for_render": approved_for_render,
        "quality_feedback": feedback,
        "metadata": metadata,
        "render_payload": render_payload,
    }
