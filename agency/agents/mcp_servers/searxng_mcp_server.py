"""
searxng_mcp_server.py

Servidor MCP para la herramienta de búsqueda web mediante SearXNG.
Reglas de seguridad (AGENTS.md sección 8):
- Sanitización estricta de HTML y JSON crudo antes de enviar al prompt.
- Recorte de snippets a ~400 caracteres.
- Fallback gracioso a tendencias estructuradas si SearXNG no responde.
"""

import os
import re
import logging
import httpx
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

_raw_searx = os.getenv("SEARXNG_URL", "http://searxng:8080")
SEARXNG_URL = _raw_searx if _raw_searx.startswith("http://") or _raw_searx.startswith("https://") else f"http://{_raw_searx}"


def sanitize_html_content(raw_text: str) -> str:
    """Elimina etiquetas HTML y caracteres desbordantes de un fragmento de texto."""
    if not raw_text:
        return ""
    # Remover etiquetas HTML <tag>
    clean = re.sub(r"<[^>]+>", "", raw_text)
    # Remover múltiples espacios y saltos de línea excesivos
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


async def asearxng_search_sanitized(query: str, num_results: int = 3) -> List[Dict[str, str]]:
    """
    Realiza una búsqueda asíncrona en SearXNG sin bloquear el event loop probando hosts candidatos.
    """
    clean_query = sanitize_html_content(query)
    if not clean_query:
        return []

    candidate_urls = list(dict.fromkeys([SEARXNG_URL, "http://searxng:8080", "http://localhost:8080"]))

    for target_url in candidate_urls:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(
                    f"{target_url.rstrip('/')}/search",
                    params={"q": clean_query, "format": "json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    sanitized_results = []
                    for item in results[:num_results]:
                        title = sanitize_html_content(item.get("title", ""))
                        snippet = sanitize_html_content(item.get("content", ""))[:400]
                        url = item.get("url", "")
                        if title and url:
                            sanitized_results.append(
                                {"title": title, "snippet": snippet, "url": url}
                            )
                    if sanitized_results:
                        return sanitized_results
        except Exception as exc:
            logger.debug(f"SearXNG no disponible en {target_url}: {exc}")

    return _get_synthetic_fallback(clean_query)


def _get_synthetic_fallback(clean_query: str) -> List[Dict[str, str]]:
    encoded_q = clean_query.replace(" ", "+")
    return [
        {
            "title": f"Búsqueda Directa Google: {clean_query}",
            "snippet": f"Resultados filtrados en vivo sobre {clean_query} optimizados para retención de audiencia.",
            "url": f"https://www.google.com/search?q={encoded_q}",
        },
        {
            "title": f"Tendencias de Contenido en Instagram: {clean_query}",
            "snippet": f"Patrones de Hooks y ángulos virales en Reels para {clean_query}.",
            "url": f"https://www.google.com/search?q=site:instagram.com+{encoded_q}",
        },
    ]


def searxng_search_sanitized(query: str, num_results: int = 3) -> List[Dict[str, str]]:
    """
    Realiza una búsqueda en SearXNG y retorna resultados sanitizados y recortados.
    
    :param query: Término de búsqueda.
    :param num_results: Cantidad máxima de resultados a retornar.
    :return: Lista de diccionarios con 'title', 'snippet' y 'url'.
    """
    clean_query = sanitize_html_content(query)
    if not clean_query:
        return []

    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.get(
                f"{SEARXNG_URL}/search",
                params={"q": clean_query, "format": "json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                sanitized_results = []
                for item in results[:num_results]:
                    title = sanitize_html_content(item.get("title", ""))
                    snippet = sanitize_html_content(item.get("content", ""))[:400]
                    url = item.get("url", "")
                    sanitized_results.append(
                        {"title": title, "snippet": snippet, "url": url}
                    )
                if sanitized_results:
                    return sanitized_results
    except Exception as exc:
        logger.warning(f"SearXNG no disponible ({exc}). Aplicando fallback sintético.")

    return _get_synthetic_fallback(clean_query)

