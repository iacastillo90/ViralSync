"""
agents/mcp_servers/searxng_mcp_server.py

Servidor MCP que expone la búsqueda web vía SearXNG local, sanitizada
antes de llegar a cualquier LLM.

AGENTS.md, sección 8, regla explícita:
  "Todo contenido que venga de una búsqueda web debe pasar por el wrapper
   de sanitización antes de llegar al LLM — nunca HTML o JSON crudo de
   SearXNG directo al prompt."

Y sección 8 (tools compartidas -> MCP):
  cualquier tool consumida por más de un agente/framework se expone aquí,
  no como @tool embebido en agents/tools/ (patrón legacy).

Se usa principalmente en el nodo de ideación (AGENTS.md 7.7, validación en
los 4 cuadrantes: on-nicho/off-nicho x on-plataforma/off-plataforma).

Correr con:  python -m agents.mcp_servers.searxng_mcp_server
"""

from __future__ import annotations

import os
import re
import html
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")
MAX_SNIPPET_CHARS = 400
MAX_RESULTS = 8

mcp = FastMCP("searxng-tools")


def _strip_html(raw: str) -> str:
    """Quita tags HTML y colapsa espacios — nunca pasar markup crudo a un LLM."""
    no_tags = re.sub(r"<[^>]+>", " ", raw or "")
    unescaped = html.unescape(no_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def _sanitize_result(item: dict[str, Any]) -> dict[str, str]:
    title = _strip_html(item.get("title", ""))[:150]
    snippet = _strip_html(item.get("content", ""))[:MAX_SNIPPET_CHARS]
    url = item.get("url", "")
    return {"title": title, "snippet": snippet, "url": url}


@mcp.tool()
def buscar_tendencias_searxng(query: str, categoria: str = "general") -> list[dict[str, str]]:
    """
    Busca en la web (vía SearXNG local, sin API keys de terceros) y devuelve
    resultados sanitizados: título recortado + snippet recortado a ~400
    caracteres, sin HTML/markup. Usar para validar ideas contra referencias
    reales antes de darlas por buenas (AGENTS.md 7.7): dentro/fuera de
    nicho, dentro/fuera de la plataforma de destino.

    Args:
        query: términos de búsqueda, cortos y específicos.
        categoria: categoría de SearXNG (general, news, social media si el
            engine lo soporta).
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "categories": categoria, "format": "json"},
        )
        resp.raise_for_status()
        raw_results = resp.json().get("results", [])[:MAX_RESULTS]

    return [_sanitize_result(r) for r in raw_results]


@mcp.tool()
def validar_cuadrante_competencia(idea_texto: str, nicho: str, plataforma: str) -> dict:
    """
    Corre las 4 búsquedas del análisis de competencia (AGENTS.md 7.7):
    on-nicho/off-nicho x on-plataforma/off-plataforma, y devuelve evidencia
    sanitizada de cada cuadrante para que el agente de ideación decida con
    datos reales, no inventando patrones.
    """
    cuadrantes = {
        "on_nicho_on_plataforma": f"{idea_texto} {nicho} {plataforma}",
        "on_nicho_off_plataforma": f"{idea_texto} {nicho}",
        "off_nicho_on_plataforma": f"{idea_texto} {plataforma} viral",
        "off_nicho_off_plataforma": f"{idea_texto} viral",
    }
    return {clave: buscar_tendencias_searxng(q) for clave, q in cuadrantes.items()}


if __name__ == "__main__":
    mcp.run()
