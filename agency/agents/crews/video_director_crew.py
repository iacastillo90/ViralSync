"""
video_director_crew.py

Crew Director de Video de ViralSync (CrewAI):
Actúa como Guardián de Calidad y Rendimiento Final:
1. Filtro de Valor (Impacto RUM): Evalúa retención y densidad de valor antes de autorizar renderizado.
2. Filtro de Hardware: Limita la duración a 45 segundos y fuerza clips ligeros (720p/1080p).
3. Curaduría de Metadatos: Redacta títulos persuasivos, descripciones empáticas y hashtags de nicho.

PR-B / WU3: la curaduría se vuelve contextual vía el router compartido
``agents.llm.acomplete()``, gated por ``check_tenant_llm_budget`` sobre
``llm_spend:{tenant_id}`` (espejo de dm_response.py:62-72, D5), con parse
estricto (D6) y plantilla determinística como fallback (REQ-CVD-01/02).
"""

import asyncio
import json
import logging
import os
import re
import threading
from typing import Dict, Any, List, Tuple, Optional

import agents.llm as llm

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


def _tenant_within_llm_budget(tenant_id: str) -> bool:
    """D5 — Guard de presupuesto por tenant (espejo de dm_response.py:62-72).

    Lee el gasto acumulado de ``llm_spend:{tenant_id}`` en Redis y consulta
    ``check_tenant_llm_budget``. Redis caído → warning + continuar sin guard
    (REQ-CVD-02-3). Devuelve True si el tenant puede gastar en LLM.
    """
    try:
        import redis as _redis
        from backend.services.llm_budget_service import check_tenant_llm_budget

        _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            _r = _redis.Redis.from_url(_redis_url, socket_timeout=1.0)
            accumulated = float(_r.get(f"llm_spend:{tenant_id}") or 0.0)
            if not check_tenant_llm_budget(tenant_id, accumulated):
                logger.warning(
                    f"[{tenant_id}] Presupuesto LLM mensual excedido (${accumulated:.2f}). "
                    "El Director usa curaduría plantilla y no gasta tokens."
                )
                return False
        except _redis.RedisError as _re:
            logger.warning(
                f"[{tenant_id}] Redis no disponible para verificar presupuesto ({_re}). "
                "Continuando sin guard."
            )
    except Exception as _e:
        logger.warning(f"[{tenant_id}] No se pudo verificar presupuesto LLM ({_e}). Continuando sin guard.")
    return True


def _parse_metadata_json(content: str) -> Optional[Dict[str, Any]]:
    """D6 — Parse estricto de la respuesta del router (REQ-CVD-01).

    Quita fences ```, exige JSON con ``final_title``/``description``/
    ``hashtags``/``keywords`` tipados. Cualquier fallo → None (→ plantilla).
    """
    if not content:
        return None
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    final_title = data.get("final_title")
    description = data.get("description")
    hashtags = data.get("hashtags")
    keywords = data.get("keywords")
    if not isinstance(final_title, str) or not final_title.strip():
        return None
    if not isinstance(description, str) or not description.strip():
        return None
    if not isinstance(hashtags, list) or not all(isinstance(h, str) and h.strip() for h in hashtags):
        return None
    if not isinstance(keywords, list) or not all(isinstance(k, str) and k.strip() for k in keywords):
        return None
    return {
        "final_title": final_title.strip(),
        "description": description.strip(),
        "hashtags": [h.strip() for h in hashtags],
        "keywords": [k.strip() for k in keywords],
        "full_caption": f"{description.strip()}\n\n" + " ".join(h.strip() for h in hashtags),
    }


async def curate_video_metadata_llm(
    script: Dict[str, Any],
    idea: Dict[str, Any],
    tenant_id: str,
    template_metadata: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """REQ-CVD-01 — Curaduría contextual vía el router compartido.

    Gated por el guard de presupuesto (D5). Devuelve los 4 campos curados o
    None (plantilla) cuando el presupuesto está agotado, el router falla por
    completo o la respuesta no parsea (D6).
    """
    if not _tenant_within_llm_budget(tenant_id):
        return None

    niche = idea.get("niche", "Marketing SaaS")
    idea_title = idea.get("texto", "Estrategia de Crecimiento")
    gancho = script.get("gancho_0_5s", "").strip()

    system_prompt = (
        "Eres el Director de Video de ViralSync. Eres un curador de metadatos para Reels "
        "verticales 9:16. Responde SOLO con JSON estricto, sin markdown, con estas claves: "
        '"final_title", "description", "hashtags", "keywords". '
        "final_title: título persuasivo (máx 65 caracteres). description: descripción empática "
        "con gancho y CTA (2-4 oraciones). hashtags: lista de 4-8 strings que empiezan con '#'. "
        "keywords: lista de 2-6 strings en inglés para el b-roll."
    )
    user_prompt = (
        f"Niche: {niche}\nIdea: {idea_title}\nGancho: {gancho}\n\n"
        f"Plantilla actual (mejórala sin inventar datos):\n"
        f"Título: {template_metadata.get('final_title', '')}\n"
        f"Descripción: {template_metadata.get('description', '')}\n\n"
        "Devuelve el JSON estricto."
    )

    try:
        content = (
            await llm.acomplete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )
        ).strip()
        curated = _parse_metadata_json(content)
        if curated is None:
            logger.warning(f"[{tenant_id}] Director: respuesta LLM no parseable; usando plantilla.")
        return curated
    except Exception as exc:
        logger.warning(f"[{tenant_id}] Router LLM no disponible para curaduría ({exc}). Usando plantilla.")
        return None


def _run_async_curation(
    script: Dict[str, Any],
    idea: Dict[str, Any],
    tenant_id: str,
    template_metadata: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """D4 — Puente sync↔async.

    Conduce la curaduría async en un event loop PRIVADO. En Python 3.12 un
    ``new_event_loop().run_until_complete()`` en el MISMO hilo falla si ya hay
    un loop corriendo (``_check_running``, contexto nodo LangGraph async), así
    que el loop privado se crea y corre en un hilo de trabajo: el estado
    "running loop" de asyncio es thread-local, por lo que es legal tanto desde
    Celery-sync como desde dentro de un loop en ejecución (node_video_edit).
    """
    outcome: Dict[str, Any] = {}

    def _target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            outcome["value"] = loop.run_until_complete(
                curate_video_metadata_llm(script, idea, tenant_id, template_metadata)
            )
        except BaseException as exc:  # noqa: BLE001 - se propaga al hilo llamador
            outcome["error"] = exc
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()

    thread = threading.Thread(target=_target, name=f"director-llm-{tenant_id}", daemon=True)
    thread.start()
    thread.join()
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


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

    # 2. Curaduría de Metadatos: base determinística (plantilla) + curaduría
    #    contextual LLM con guard de presupuesto (WU3, D4/D5/D6). Solo se gasta
    #    si el guion fue aprobado (nunca tokens para contenido rechazado).
    metadata = curate_video_metadata(script, idea)
    curated = None
    if approved_for_render:
        curated = _run_async_curation(script, idea, tenant_id, metadata)
        if curated:
            metadata = curated
            logger.info(f"[{tenant_id}] Director: metadatos curados contextualmente por LLM.")

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

    if curated and curated.get("keywords"):
        keywords = curated["keywords"]
    else:
        keywords = extract_keywords_from_script(full_script_text, metadata["final_title"])

    render_payload = {
        "title": metadata["final_title"],
        "script_text": full_script_text,
        "keywords": keywords,
        "tenant_id": tenant_id,
        "max_duration_seconds": MAX_VIDEO_DURATION_SECONDS,
        "requested_resolution": "720p",
        # WU3/D6: aditivo — el renderer antiguo ignora estas claves (extra='ignore')
        "description": metadata.get("description", ""),
        "hashtags": metadata.get("hashtags", []),
    }

    return {
        "tenant_id": tenant_id,
        "quality_score": quality_score,
        "approved_for_render": approved_for_render,
        "quality_feedback": feedback,
        "metadata": metadata,
        "render_payload": render_payload,
    }
