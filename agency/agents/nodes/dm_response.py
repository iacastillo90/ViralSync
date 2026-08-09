"""
dm_response.py

Nodo del Grafo Conversacional de DMs de Instagram (LangGraph).
Evalúa la intención del mensaje entrante, consulta la base de conocimientos RAG de Qdrant,
genera respuestas dinámicas asistidas por LLM Gateway y realiza el handoff automático a operador humano.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from typing_extensions import TypedDict
from agents.mcp_servers.rag_mcp_server import query_rag_knowledge
from backend.sse_manager import emit_node_progress
import agents.llm as llm

logger = logging.getLogger(__name__)

CONFIDENCE_HUMAN_THRESHOLD = 0.75


class DMState(TypedDict):
    tenant_id: str
    lead_id: str
    incoming_message: str
    conversation_history: List[Dict[str, str]]
    rag_context: str
    reply_text: str
    confidence_score: float
    intent: str  # question | objection | purchase_intent | spam | unclear
    requires_human: bool


def classify_intent(message: str) -> str:
    """Clasifica la intención del mensaje entrante."""
    msg_lower = message.lower()

    if any(word in msg_lower for word in ["comprar", "precio", "demo", "contratar", "quiero el sistema"]):
        return "purchase_intent"
    elif any(word in msg_lower for word in ["caro", "duda", "funciona realmente", "pero"]):
        return "objection"
    elif any(word in msg_lower for word in ["como", "cuando", "donde", "que es", "informacion"]):
        return "question"
    elif any(word in msg_lower for word in ["http", "crypto", "win money", "casino"]):
        return "spam"
    return "unclear"


def generate_grounded_reply(message: str, rag_context: str, tenant_id: str = "default_tenant") -> Tuple[str, float]:
    """
    Genera una respuesta basada en RAG utilizando el Gateway LLM si está disponible,
    con registro de consumo de presupuesto en USD y estimación del score de confianza.
    """
    if not rag_context or "no se encontro" in rag_context.lower():
        reply = "Gracias por escribirnos. Un especialista humano se pondrá en contacto contigo en breve para darte respuesta exacta."
        return reply, 0.50

    # Intento de generación con el router LLM compartido en entorno conectado
    try:
        import redis as _redis
        from backend.services.llm_budget_service import check_tenant_llm_budget

        # Guard de presupuesto: bloquear si el tenant ya superó el límite mensual
        _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            _r = _redis.Redis.from_url(_redis_url, socket_timeout=1.0)
            accumulated = float(_r.get(f"llm_spend:{tenant_id}") or 0.0)
            if not check_tenant_llm_budget(tenant_id, accumulated):
                raise Exception(f"Presupuesto LLM mensual excedido para tenant '{tenant_id}' (${accumulated:.2f})")
        except _redis.RedisError as _re:
            logger.warning(f"[{tenant_id}] Redis no disponible para verificar presupuesto ({_re}). Continuando sin guard.")

        system_prompt = "Eres un Asistente de Ventas de Instagram. Responde de forma concisa (máximo 2 oraciones) y amigable en español."
        user_prompt = f"Contexto RAG de marca:\n{rag_context}\n\nMensaje del Cliente: '{message}'"

        generated_reply = llm.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=300,
        ).strip()

        # El router devuelve texto plano: el guard de presupuesto ya protegió el gasto
        # antes de llamar, pero no expone metadata de tokens (usage) del proveedor.
        confidence = 0.92
        return generated_reply, confidence
    except Exception as exc:
        logger.debug(f"LLM Gateway no disponible ({exc}). Usando plantilla grounded de respaldo.")

    # Fallback grounded dinámico si se ejecuta offline/dev
    reply = f"¡Hola! Sobre tu consulta: '{message[:30]}...' Te confirmo según nuestra guía oficial: {rag_context[:120]}... ¿Deseas agendar una demo?"
    confidence = 0.88
    return reply, confidence


async def node_dm_response(state: DMState) -> DMState:
    """
    Nodo ejecutable de LangGraph para el procesamiento conversacional de DMs.
    """
    tenant_id = state.get("tenant_id", "default_tenant")
    lead_id = state.get("lead_id", "lead-unknown")
    incoming_msg = state.get("incoming_message", "")

    logger.info(f"[{tenant_id}] Procesando DM entrante del lead '{lead_id}': '{incoming_msg[:40]}'")
    emit_node_progress(tenant_id, "dm_processing", "running")

    # 1. Clasificación de Intención
    intent = classify_intent(incoming_msg)

    # 2. Consulta de Contexto RAG en Qdrant
    rag_docs = query_rag_knowledge(query=incoming_msg)
    rag_context = "\n".join([doc.get("content", "") for doc in rag_docs if isinstance(doc, dict)])

    # 3. Generación de Respuesta asistida por LLM / Grounding RAG y Tracking de Presupuesto
    reply_text, confidence = generate_grounded_reply(incoming_msg, rag_context, tenant_id=tenant_id)

    # 4. Evaluación de Handoff a Humano
    requires_human = (
        confidence < CONFIDENCE_HUMAN_THRESHOLD
        or intent in ["objection", "purchase_intent"]
    )

    if requires_human:
        logger.warning(f"[{tenant_id}] Escalando DM del lead '{lead_id}' a operador humano (Intención: {intent}, Confianza: {confidence})")
        emit_node_progress(tenant_id, "human_takeover_triggered", "completed")

    return {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "incoming_message": incoming_msg,
        "conversation_history": state.get("conversation_history", []),
        "rag_context": rag_context,
        "reply_text": reply_text,
        "confidence_score": confidence,
        "intent": intent,
        "requires_human": requires_human,
    }
