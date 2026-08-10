"""
prompt_context.py

Shared prompt-context helpers for the writer crews (design D7, REQ-CVD-03/04):

- ``resolve_rum_threshold(niche)``: niche RUM dynamic threshold from Redis
  (``rum_threshold:{niche}``, clamped [0.50, 0.90], default 0.70). Thin wrapper
  over ``get_dynamic_threshold`` — the clamp and default live in rum_calculator;
  no new constant is introduced here (CVD-03-2). Redis down degrades to the
  clamp default, never a hardcoded global.
- ``build_trend_section(niche)``: daily-scraped trends from
  ``rag_cache["tendencia_{niche}"]`` (written by trend_scraper_task.py),
  sanitized through the HTML sanitization wrapper and trimmed to <=400 chars.
  Cache miss or Redis failure returns "" so the crew still produces output
  (CVD-04-2, non-fatal).
"""

import logging

from agents.criterion.rum_calculator import get_dynamic_threshold
from agents.mcp_servers.searxng_mcp_server import sanitize_html_content
from backend.cache.rag_cache import rag_cache

logger = logging.getLogger(__name__)

# Snippet trim matches the SearXNG MCP server rule ("~400 chars").
MAX_TREND_SNIPPET_CHARS = 400


def resolve_rum_threshold(niche: str) -> float:
    """
    Resolve the niche RUM dynamic threshold from Redis (CVD-03).

    Delegates to ``get_dynamic_threshold``, which reads ``rum_threshold:{niche}``
    and applies the [0.50, 0.90] clamp with the 0.70 default. The last-resort
    guard below only mirrors that default when the getter itself fails; it never
    injects a new hardcoded constant.
    """
    try:
        return float(get_dynamic_threshold(niche))
    except Exception as exc:
        logger.warning(
            f"No se pudo resolver el umbral RUM para '{niche}' ({exc}). "
            "Usando el clamp default (CVD-03-2)."
        )
        return 0.70


def build_trend_section(niche: str) -> str:
    """
    Build the sanitized trend snippet section, or "" on miss (CVD-04).

    Reads ``rag_cache["tendencia_{niche}"]``; each document goes through the
    sanitization wrapper (``sanitize_html_content``) and the whole section is
    trimmed to <=400 chars. Missing or malformed entries, a cache miss, or a
    Redis failure all produce "" — never an exception.
    """
    try:
        docs = rag_cache.get(f"tendencia_{niche}")
    except Exception as exc:
        logger.warning(
            f"Caché de tendencias no disponible para '{niche}' ({exc}). "
            "Omitiendo sección de tendencias (CVD-04-2)."
        )
        return ""

    if not docs:
        return ""

    lines = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        content = doc.get("content") or doc.get("title") or ""
        snippet = sanitize_html_content(str(content))
        if snippet:
            lines.append(f"- {snippet[:MAX_TREND_SNIPPET_CHARS]}")

    if not lines:
        return ""

    section = "\n".join(lines)
    return section[:MAX_TREND_SNIPPET_CHARS]
