"""
analytics_agent.py

Agente de Analítica de Rendimiento 72h y Aprendizaje Continuo RAG (ViralSync Enterprise).
Rastrea la viralidad de las publicaciones a las 72h, identifica patrones con alta tasa de conversión
y retroalimenta la memoria vectorial en Qdrant (`marketing_brain`) para optimizar futuros guiones.
"""

import os
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")


class PerformanceAnalyticsAgent:
    """
    Agente evaluador de métricas post-publicación.
    Clasifica el contenido y retroalimenta la base vectorial RAG en Qdrant.
    """

    def calculate_viral_score(self, views_72h: int, followers_gained: int) -> float:
        """Calcula una puntuación de viralidad normalizada (0.0 a 1.0)."""
        views_score = min(1.0, views_72h / 50000.0)
        conversion_score = min(1.0, followers_gained / 500.0)
        return round((views_score * 0.7) + (conversion_score * 0.3), 3)

    def evaluate_video_performance(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa el desempeño de una pieza a las 72 horas y decide si alimentar Qdrant.
        """
        tenant_id = video_data.get("tenant_id", "default_tenant")
        video_id = video_data.get("video_id", "video_001")
        views_72h = video_data.get("views_72h", 12500)
        followers_gained = video_data.get("followers_gained", 120)
        gancho_text = video_data.get("gancho_text", "")

        viral_score = self.calculate_viral_score(views_72h, followers_gained)
        is_proven_viral = viral_score >= 0.35

        classification = "Viral High-Performer" if is_proven_viral else "Standard Performance"

        logger.info(
            f"[{tenant_id}] Video {video_id} evaluado a las 72h: Score={viral_score} | "
            f"Clasificación='{classification}'"
        )

        rag_feedback_status = "Skipped"
        if is_proven_viral and gancho_text:
            rag_feedback_status = self.feed_winning_pattern_to_qdrant(
                tenant_id=tenant_id,
                pattern_text=gancho_text,
                viral_score=viral_score
            )

        return {
            "status": "COMPLETED",
            "video_id": video_id,
            "tenant_id": tenant_id,
            "viral_score": viral_score,
            "classification": classification,
            "rag_feedback_status": rag_feedback_status,
        }

    def feed_winning_pattern_to_qdrant(self, tenant_id: str, pattern_text: str, viral_score: float, niche: str = "") -> str:
        """
        Indexa una estructura de guion exitosa en la colección `marketing_brain` de Qdrant.
        """
        try:
            from backend.services.rag_context import index_winning_pattern
            success = index_winning_pattern(
                tenant_id=tenant_id,
                pattern_text=pattern_text,
                viral_score=viral_score,
                niche=niche,
            )
            return "SUCCESS_RAG_INDEXED" if success else "ERROR_RAG_INDEXING"
        except Exception as exc:
            logger.error(f"[{tenant_id}] Error indexando patrón ganador en Qdrant: {exc}")
            return "ERROR_RAG_INDEXING"


def analytics_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Nodo del grafo encargado de la evaluación 72h y retroalimentación RAG."""
    agent = PerformanceAnalyticsAgent()
    video_data = state.get("video_data") or state
    output = agent.evaluate_video_performance(video_data)
    return {"analytics_result": output}
