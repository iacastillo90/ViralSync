"""
Módulo de Servidores MCP (Model Context Protocol) de ViralSync.
Herramientas agnósticas consumibles por CrewAI, LangGraph o cualquier framework.
"""

from .searxng_mcp_server import searxng_search_sanitized, sanitize_html_content
from .rag_mcp_server import query_rag_knowledge, simple_embedding

__all__ = [
    "searxng_search_sanitized",
    "sanitize_html_content",
    "query_rag_knowledge",
    "simple_embedding",
]
