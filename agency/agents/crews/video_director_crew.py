"""
video_director_crew.py

Crew Director de Video de ViralSync (CrewAI):
Agente especializado en analizar el guion de 4 bloques producido por scriptwriting_crew.py,
extraer palabras clave visuales precisas para B-roll y formatear el payload JSON
para el microservicio de renderizado faceless (MoneyPrinter).
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def extract_keywords_from_script(script_text: str, idea_title: str) -> List[str]:
    """Extrae palabras clave visuales precisas orientadas a búsqueda en Pexels API."""
    base_terms = ["business", "technology", "office", "success", "entrepreneur", "marketing", "growth"]
    
    # Palabras clave adicionales basadas en el título de la idea
    title_words = [w.lower() for w in re.findall(r"\b\w{4,}\b", idea_title)]
    keywords = list(dict.fromkeys(title_words + base_terms))[:4]
    
    logger.info(f"Palabras clave visuales extraídas para el video: {keywords}")
    return keywords


def run_video_director_crew(
    script: Dict[str, Any], idea: Dict[str, Any], tenant_id: str = "default_tenant"
) -> Dict[str, Any]:
    """
    Toma el resultado final del equipo de guionismo, formatea el JSON requerido
    por el microservicio de renderizado y prepara el payload para la cola asíncrona.

    :param script: Diccionario con los 4 bloques del guion (gancho_0_5s, contexto_5_30s, moraleja_30_50s, cta_50_60s).
    :param idea: Diccionario con la idea aprobada (texto, gancho, etc).
    :param tenant_id: ID del tenant.
    :return: Payload JSON estructurado listo para enviar a POST /render.
    """
    logger.info(f"[{tenant_id}] Ejecutando Agente Director de Video (VideoDirectorAgent)")

    title = idea.get("texto", "Video Marketing ViralSync")
    
    # Unir los 4 bloques del guion en un texto continuo para la narración Edge-TTS
    gancho = script.get("gancho_0_5s", "")
    contexto = script.get("contexto_5_30s", "")
    moraleja = script.get("moraleja_30_50s", "")
    cta = script.get("cta_50_60s", "")

    full_script_text = f"{gancho} {contexto} {moraleja} {cta}".strip()
    if not full_script_text:
        full_script_text = "Descubre cómo escalar tu negocio con automatización e inteligencia artificial hoy mismo."

    # Extraer palabras clave para la búsqueda de clips en Pexels
    keywords = extract_keywords_from_script(full_script_text, title)

    render_payload = {
        "title": title,
        "script_text": full_script_text,
        "keywords": keywords,
        "tenant_id": tenant_id,
    }

    logger.info(f"[{tenant_id}] Payload preparado por el Agente Director para /render: {title}")
    return render_payload
