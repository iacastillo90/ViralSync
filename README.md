# ViralSync — Sistema Multiagente de Marketing Inbound & Automatización de Contenido

ViralSync es una plataforma SaaS multi-tenant que automatiza el ciclo completo de marketing de contenido para redes sociales: investigación de mercado, ideación basada en datos reales, scoring RUM, guionismo estructurado, post-producción de video, publicación oficial vía Instagram Graph API y captura de leads en tiempo real mediante webhooks.

## 🚀 Arquitectura del Sistema
- **Orquestación:** LangGraph (StateGraph multi-tenant persistido en PostgreSQL)
- **Ejecución Creativa:** CrewAI (Crews especializadas por nodo)
- **Gateway LLM:** LiteLLM Proxy (Pool gratuito + fallback pagado único)
- **Búsqueda Web:** SearXNG (vía MCP Server)
- **Memoria / RAG:** Qdrant (vía MCP Server)
- **Cola de Trabajos:** Redis + Celery (`--concurrency=1` en dev)
- **Backend:** FastAPI (REST + Webhooks Meta HMAC + SSE Realtime)
- **Frontend:** Next.js 14 + Tailwind CSS + Lucide Icons

## 🛠️ Inicio Rápido
```bash
# Levantar stack completo con Docker
docker compose up -d

# Levantar backend FastAPI
uvicorn agency.backend.main:app --reload --port 8000

# Levantar frontend Next.js
cd agency/frontend && npm run dev
```
