"""
trend_scraper_task.py

Tarea Celery de Combustible Dinámico de Tendencias para ViralSync (Cron Job Diario).
Busca temas virales en internet vía SearXNG y actualiza automáticamente el contexto RAG en Qdrant.
"""

import logging
from typing import Dict, Any, List
from workers.celery_app import celery_app
from agents.mcp_servers.searxng_mcp_server import searxng_search_sanitized
from backend.cache.rag_cache import rag_cache

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.trend_scraper_task.scrape_daily_marketing_trends")
def scrape_daily_marketing_trends(niche: str = "B2B SaaS Marketing") -> Dict[str, Any]:
    """
    Tarea Celery diaria que busca tendencias frescas en internet y las inyecta a la memoria RAG.

    :param niche: Nicho objetivo de búsqueda.
    :return: Estado de la actualización e ítems procesados.
    """
    logger.info(f"Iniciando raspado diario de tendencias virales para nicho '{niche}'...")

    search_query = f"viral reels trends growth hacks {niche} 2026"
    results = searxng_search_sanitized(query=search_query, num_results=5)

    ingested_trends = []
    for item in results:
        trend_doc = {
            "filename": f"trend_{item.get('title', 'general')[:20].lower().replace(' ', '_')}.md",
            "content": f"Tendencia Viral Actual: {item.get('title')} - {item.get('snippet')}",
            "source_url": item.get("url", ""),
            "niche": niche,
        }
        ingested_trends.append(trend_doc)
        # Invalidar o inyectar en la memoria RAG
        rag_cache.set(f"tendencia_{niche}", [trend_doc], ttl=86400)

    logger.info(f"Se actualizaron {len(ingested_trends)} tendencias dinámicas en el contexto RAG.")
    return {
        "status": "success",
        "niche": niche,
        "trends_count": len(ingested_trends),
        "trends": ingested_trends,
    }
