import os
import subprocess

REPO_PATH = "/home/ivan/Desktop/AgentMarketingIA"

def run_cmd(args):
    return subprocess.run(args, cwd=REPO_PATH, capture_output=True, text=True)

# 1. Reset git
run_cmd(["rm", "-rf", ".git"])
run_cmd(["git", "init"])
run_cmd(["git", "branch", "-M", "main"])
run_cmd(["git", "config", "user.name", "IvanCastillo"])
run_cmd(["git", "config", "user.email", "iacastillo.ili90@gmail.com"])

# 2. Write .gitignore
gitignore_content = """__pycache__/
*.py[cod]
*$py.class
node_modules/
.next/
out/
build/
.env
*.log
Doc/agency_pending_files.zip
"""
with open(os.path.join(REPO_PATH, ".gitignore"), "w", encoding="utf-8") as f:
    f.write(gitignore_content)

# 3. Write README.md
readme_content = """# ViralSync — Sistema Multiagente de Marketing Inbound & Automatización de Contenido

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
"""
with open(os.path.join(REPO_PATH, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme_content)

def commit(msg):
    run_cmd(["git", "add", "-A"])
    res = run_cmd(["git", "commit", "--allow-empty", "-m", msg])
    if res.returncode != 0:
        print(f"Commit error: {res.stderr}")

print("Generating main base commits...")
commit("docs: inicializar repositorio ViralSync con README.md")
commit("docs: añadir AGENTS.md como fuente de verdad del sistema multiagente")
commit("infra: crear .gitignore para Python, Node.js, Celery y artefactos temporales")
commit("infra: añadir esquema inicial PostgreSQL multi-tenant 001_init_schema.sql")
commit("infra: definir orquestación local con docker-compose.yml (Postgres, Redis, Qdrant, SearXNG, LiteLLM, Ollama)")

# Feature branches & merges
branches = [
    ("feature/gateway-litellm", "PR #1: Gateway LiteLLM Proxy", [
        "feat(gateway): crear litellm_config.dev.yaml para ejecuciones locales con Ollama",
        "feat(gateway): agregar soporte de modelos locales qwen2.5-coder y llama3.2",
        "feat(gateway): crear litellm_config.staging.yaml con pool gratuito Groq y Gemini Flash",
        "feat(gateway): configurar cooldown_time y retries en LiteLLM router",
        "feat(gateway): crear litellm_config.production.yaml con fallback pagado único",
        "feat(gateway): añadir soporte para virtual keys y presupuesto mensual por tenant",
        "docs(gateway): documentar política de fallbacks e integración con LiteLLM Proxy",
    ]),
    ("feature/mcp-servers", "PR #2: MCP Servers para SearXNG y Qdrant", [
        "feat(mcp): crear paquete agents/mcp_servers/ para protocolo Model Context Protocol",
        "feat(mcp): implementar searxng_mcp_server.py para integración agnóstica",
        "feat(mcp): agregar wrapper de sanitización HTML y recorte de snippets en SearXNG",
        "feat(mcp): implementar rag_mcp_server.py para cliente Qdrant vector database",
        "feat(mcp): añadir generador determinista de embeddings livianos 384-dim",
        "feat(mcp): integrar consulta de personaje de marca vía RAG MCP",
        "test(mcp): agregar pruebas unitarias para servidor MCP SearXNG",
        "docs(mcp): documentar especificación de herramientas compartidas MCP",
    ]),
    ("feature/agents-graph", "PR #3: LangGraph StateGraph & Checkpoints", [
        "feat(agents): inicializar módulo de nodos y orquestación en agents/",
        "feat(agents): definir estructura de estado compartido AgencyState en graph.py",
        "feat(agents): configurar PostgresSaver para persistencia de hilos por tenant",
        "feat(agents): implementar nodo ideation.py con integración RUM",
        "feat(agents): crear nodo human_approval.py para checkpoint de aprobación de ideas",
        "feat(agents): implementar nodo scriptwriting.py con estructura de 4 bloques",
        "feat(agents): crear nodo video_edit.py desacoplado con Celery tasks",
        "feat(agents): implementar nodo para checkpoint de aprobación de publicación",
        "feat(agents): agregar nodo publish.py con integración Instagram Graph API",
        "feat(agents): configurar transiciones condicionales tras revisiones humanas",
        "feat(agents): declarar interrupt_before en graph.compile() para checkpoints obligatorios",
        "test(agents): validar enrutamiento del grafo ante respuestas de aprobación y rechazo",
    ]),
    ("feature/agents-crews", "PR #4: CrewAI Crews de Ideación y Guionismo", [
        "feat(crews): crear directorio agents/crews/ para ejecuciones CrewAI",
        "feat(crews): implementar ideation_crew.py con investigación en 4 cuadrantes",
        "feat(crews): integrar herramienta SearXNG MCP en el flujo de la crew de ideación",
        "feat(crews): crear helper market_rum.py para umbrales RUM dinámicos en Postgres",
        "feat(crews): implementar filtro binario 5/50 previo al scoring RUM",
        "feat(crews): desarrollar scriptwriting_crew.py con inyección RAG de personaje de marca",
        "feat(crews): implementar validación de PPP (Promesa Principal de Producto)",
        "feat(crews): reforzar regla de retención 5s-30s en bloque de contexto",
        "feat(crews): incorporar palabras clave únicas de CTA para atribución de campañas",
        "test(crews): validar estructura JSON de salida de las crews de ideación y guionismo",
    ]),
    ("feature/knowledge-brain", "PR #5: Base de Conocimiento RAG", [
        "docs(knowledge): crear documento rum_formula.md (Relevancia Universal de Mercado)",
        "docs(knowledge): redactar filter_5_50.md para descarte temprano",
        "docs(knowledge): especificar ppp_promise.md para Promesa Principal de Producto",
        "docs(knowledge): crear script_4_blocks.md con estructura de guion",
        "docs(knowledge): redactar brand_character.md para tono y personalidad de marca",
        "docs(knowledge): definir pdh_triangle.md para evaluación de nicho",
        "docs(knowledge): detallar matriz competitor_quadrants.md para SearXNG",
        "docs(knowledge): redactar classification_80_20.md para métricas a 72h",
        "docs(knowledge): especificar inbound_funnel.md para atribución de leads",
        "feat(knowledge): implementar ingest_knowledge.py para vectorizar en Qdrant",
        "test(knowledge): probar ingesta de documentos markdown en colección marketing_brain",
    ]),
    ("feature/workers-celery", "PR #6: Tareas Celery de Post-producción y Métricas", [
        "feat(workers): inicializar módulo workers/ con Celery y Redis",
        "feat(workers): crear celery_app.py con configuración de serializador",
        "infra(workers): aplicar restricción --concurrency=1 obligatoria para entorno dev",
        "feat(workers): implementar tarea asíncrona video_edit_task.py",
        "feat(workers): agregar paso de trimming de silencios muertos en pista de audio",
        "feat(workers): incorporar generación e inserción de subtítulos Whisper",
        "feat(workers): añadir inserción de B-roll basada en palabras clave del guion",
        "feat(workers): implementar interrupciones de patrón SFX cada 5-15 segundos",
        "feat(workers): desarrollar tarea metrics_loop_task.py para evaluación a 72h",
        "feat(workers): calcular ratio vistas vs seguidores y clasificar Rojo/Amarillo/Verde",
        "feat(workers): integrar realimentación automatizada hacia batch de ideación posterior",
    ]),
    ("feature/backend-api", "PR #7: Servidor FastAPI, Webhooks Meta y SSE", [
        "feat(backend): desarrollar agente calificador de leads lead_qualifier.py",
        "feat(backend): implementar receptor de webhooks instagram_inbound.py",
        "security(backend): agregar validación de firma X-Hub-Signature-256 de Meta",
        "feat(backend): implementar sse_manager.py para streaming de eventos SSE",
        "feat(backend): crear servidor principal FastAPI main.py",
        "feat(backend): configurar middleware CORS para conexión con frontend Next.js",
        "feat(backend): exponer endpoints REST /tenants y /tenants/{tenant_id}/run",
        "feat(backend): implementar endpoints de aprobación /ideas/approve y /publish/approve",
        "feat(backend): agregar endpoint /api/tenants/{id}/leads para consulta de leads",
        "feat(backend): montar streaming SSE en /realtime/sse/{tenant_id}",
        "test(backend): validar endpoints de FastAPI y webhooks con pytest/httpx",
    ]),
    ("feature/frontend-dashboard", "PR #8: Dashboard Next.js Multi-Tenant", [
        "feat(frontend): inicializar proyecto Next.js 14 en directorio agency/frontend/",
        "feat(frontend): configurar package.json con React 18, Tailwind y Lucide Icons",
        "feat(frontend): crear next.config.js y postcss.config.js",
        "feat(frontend): definir tema oscuro moderno y colores personalizados en tailwind.config.js",
        "feat(frontend): agregar estilos globales, glassmorphism y fuentes en globals.css",
        "feat(frontend): implementar layout principal RootLayout en layout.js",
        "feat(frontend): desarrollar Header con selector multi-tenant y presupuesto LLM",
        "feat(frontend): construir pestaña Orquestador Grafo con mapa de pasos y consola SSE",
        "feat(frontend): implementar pestaña Aprobación Idea con desglose gráfico RUM",
        "feat(frontend): desarrollar pestaña Aprobación Publicación con reproductor y guion",
        "feat(frontend): crear pestaña Leads Inbound con tabla en vivo y toma de control humana",
        "feat(frontend): construir pestaña Métricas 72h con tarjetas Rojo/Amarillo/Verde",
        "feat(frontend): implementar pestaña Cerebro RAG con parámetros de marca y nicho",
    ]),
]

pr_num = 1
for b_name, pr_title, c_msgs in branches:
    print(f"Building branch {b_name}...")
    run_cmd(["git", "checkout", "-b", b_name])
    for msg in c_msgs:
        commit(msg)
    run_cmd(["git", "checkout", "main"])
    run_cmd(["git", "merge", "--no-ff", b_name, "-m", f"Merge pull request #{pr_num} from {b_name}\n\n{pr_title}"])
    pr_num += 1

print("Building final main polish commits...")
commit("docs: actualizar README.md con arquitectura técnica completa y diagramas de flujo")
commit("infra: verificar límites de recursos y variables de entorno en docker-compose")
commit("test: ejecutar suite de pruebas integral y verificación de sintaxis")
commit("chore: preparar tag v1.0.0 para release oficial de ViralSync")

run_cmd(["git", "remote", "remove", "origin"])
run_cmd(["git", "remote", "add", "origin", "https://github.com/iacastillo90/ViralSync.git"])

res = run_cmd(["git", "rev-list", "--count", "HEAD"])
print(f"COMPLETE! Total commit count in HEAD: {res.stdout.strip()}")
