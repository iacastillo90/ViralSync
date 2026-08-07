# 🗺️ Mapa Completo de Arquitectura y Código Fuente — ViralSync

> **Documentación Generada Automáticamente para Agentes de IA y Desarrolladores.**
> **Métricas del Proyecto:** 168 Archivos | 13,726 Líneas de Código Totales

---

## 📁 Estructura General del Proyecto

```text
ViralSync/
├── agency/
│   ├── agents/          # Agentes CrewAI, MCP Servers y Grafo StateGraph
│   ├── backend/         # API REST FastAPI, DB Models, Routers, Auth y SSE
│   ├── microservices/   # Microservicios Independientes (Renderer & Publisher)
│   ├── workers/         # Tareas Asíncronas y Worker de Celery
│   ├── frontend/        # Dashboard Web Next.js 15 + React 19
│   └── tests/           # Suite de Pruebas Unitarias y E2E (pytest)
└── Doc/                 # Documentación Enterprise, Schemas y Roadmaps
```

---

## 📦 Módulos, Entidades y Código por Paquete

### 📂 `.github/` (1 archivos, 52 líneas)

#### 📄 [ci.yml](file:///home/ivan/Desktop/AgentMarketingIA/.github/workflows/ci.yml)
- **Ruta Completa:** `.github/workflows/ci.yml`
- **Líneas de Código:** 52

### 📂 `Doc/` (13 archivos, 2,932 líneas)

#### 📄 [001_init_schema.sql](file:///home/ivan/Desktop/AgentMarketingIA/Doc/001_init_schema.sql)
- **Ruta Completa:** `Doc/001_init_schema.sql`
- **Líneas de Código:** 202

#### 📄 [API_CONTRACTS.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/API_CONTRACTS.md)
- **Ruta Completa:** `Doc/API_CONTRACTS.md`
- **Líneas de Código:** 298

#### 📄 [BACKEND_ARCHITECTURE.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/BACKEND_ARCHITECTURE.md)
- **Ruta Completa:** `Doc/BACKEND_ARCHITECTURE.md`
- **Líneas de Código:** 182

#### 📄 [DEVELOPERS.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/DEVELOPERS.md)
- **Ruta Completa:** `Doc/DEVELOPERS.md`
- **Líneas de Código:** 182

#### 📄 [FRONTEND_ARCHITECTURE.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/FRONTEND_ARCHITECTURE.md)
- **Ruta Completa:** `Doc/FRONTEND_ARCHITECTURE.md`
- **Líneas de Código:** 182

#### 📄 [FULL_PROJECT_ARCHITECTURE_MAP.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/FULL_PROJECT_ARCHITECTURE_MAP.md)
- **Ruta Completa:** `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`
- **Líneas de Código:** 918

#### 📄 [PROMPT_AUDITORIA_LLM.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/PROMPT_AUDITORIA_LLM.md)
- **Ruta Completa:** `Doc/PROMPT_AUDITORIA_LLM.md`
- **Líneas de Código:** 40

#### 📄 [ROADMAP_ENTERPRISE.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/ROADMAP_ENTERPRISE.md)
- **Ruta Completa:** `Doc/ROADMAP_ENTERPRISE.md`
- **Líneas de Código:** 72

#### 📄 [TESTING_STRATEGY.md](file:///home/ivan/Desktop/AgentMarketingIA/Doc/TESTING_STRATEGY.md)
- **Ruta Completa:** `Doc/TESTING_STRATEGY.md`
- **Líneas de Código:** 209

#### 📄 [generate_codebase_map.py](file:///home/ivan/Desktop/AgentMarketingIA/Doc/generate_codebase_map.py)
- **Ruta Completa:** `Doc/generate_codebase_map.py`
- **Líneas de Código:** 221
- **Descripción:** _generate_codebase_map.py_
- **Funciones Principales:** `parse_python_symbols, parse_js_symbols, scan_codebase, generate_markdown, main`

#### 📄 [graph.py](file:///home/ivan/Desktop/AgentMarketingIA/Doc/graph.py)
- **Ruta Completa:** `Doc/graph.py`
- **Líneas de Código:** 149
- **Descripción:** _agents/graph.py_
- **Clases / Entidades:** `AgencyState`
- **Funciones Principales:** `route_after_idea_approval, route_after_publish_approval, build_agency_graph, get_thread_config`

#### 📄 [instagram_inbound.py](file:///home/ivan/Desktop/AgentMarketingIA/Doc/instagram_inbound.py)
- **Ruta Completa:** `Doc/instagram_inbound.py`
- **Líneas de Código:** 150
- **Descripción:** _backend/webhooks/instagram_inbound.py_
- **Funciones Principales:** `verify_webhook, _valid_signature, _extract_keyword_and_text, receive_webhook`

#### 📄 [sse_manager.py](file:///home/ivan/Desktop/AgentMarketingIA/Doc/sse_manager.py)
- **Ruta Completa:** `Doc/sse_manager.py`
- **Líneas de Código:** 127
- **Descripción:** _backend/realtime/sse_manager.py_
- **Clases / Entidades:** `SSEManager`
- **Funciones Principales:** `_format_sse, _event_generator, stream_tenant_events, emit_node_progress, __init__, subscribe, unsubscribe, publish, _publish`

### 📂 `Raíz/` (8 archivos, 896 líneas)

#### 📄 [.coverage](file:///home/ivan/Desktop/AgentMarketingIA/.coverage)
- **Ruta Completa:** `.coverage`
- **Líneas de Código:** 101

#### 📄 [.env.example](file:///home/ivan/Desktop/AgentMarketingIA/.env.example)
- **Ruta Completa:** `.env.example`
- **Líneas de Código:** 48

#### 📄 [.gitignore](file:///home/ivan/Desktop/AgentMarketingIA/.gitignore)
- **Ruta Completa:** `.gitignore`
- **Líneas de Código:** 13

#### 📄 [.python-version](file:///home/ivan/Desktop/AgentMarketingIA/.python-version)
- **Ruta Completa:** `.python-version`
- **Líneas de Código:** 1

#### 📄 [Agents.md](file:///home/ivan/Desktop/AgentMarketingIA/Agents.md)
- **Ruta Completa:** `Agents.md`
- **Líneas de Código:** 497

#### 📄 [README.md](file:///home/ivan/Desktop/AgentMarketingIA/README.md)
- **Ruta Completa:** `README.md`
- **Líneas de Código:** 25

#### 📄 [agency_git.py](file:///home/ivan/Desktop/AgentMarketingIA/agency_git.py)
- **Ruta Completa:** `agency_git.py`
- **Líneas de Código:** 197
- **Funciones Principales:** `run_cmd, commit`

#### 📄 [requirements.txt](file:///home/ivan/Desktop/AgentMarketingIA/requirements.txt)
- **Ruta Completa:** `requirements.txt`
- **Líneas de Código:** 14

### 📂 `agency/` (3 archivos, 231 líneas)

#### 📄 [.coverage](file:///home/ivan/Desktop/AgentMarketingIA/agency/.coverage)
- **Ruta Completa:** `agency/.coverage`
- **Líneas de Código:** 76

#### 📄 [docker-compose.yml](file:///home/ivan/Desktop/AgentMarketingIA/agency/docker-compose.yml)
- **Ruta Completa:** `agency/docker-compose.yml`
- **Líneas de Código:** 144

#### 📄 [ruff.toml](file:///home/ivan/Desktop/AgentMarketingIA/agency/ruff.toml)
- **Ruta Completa:** `agency/ruff.toml`
- **Líneas de Código:** 11

### 📂 `agency/agents/` (25 archivos, 1,453 líneas)

#### 📄 [dm_graph.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/dm_graph.py)
- **Ruta Completa:** `agency/agents/dm_graph.py`
- **Líneas de Código:** 60
- **Descripción:** _dm_graph.py_
- **Funciones Principales:** `node_send_dm_reply, node_human_takeover, route_after_dm_response, build_dm_graph`

#### 📄 [graph.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/graph.py)
- **Ruta Completa:** `agency/agents/graph.py`
- **Líneas de Código:** 68
- **Descripción:** _graph.py_
- **Clases / Entidades:** `AgencyState`
- **Funciones Principales:** `build_agency_graph`

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/mcp_servers/__init__.py)
- **Ruta Completa:** `agency/agents/mcp_servers/__init__.py`
- **Líneas de Código:** 14
- **Descripción:** _Módulo de Servidores MCP (Model Context Protocol) de ViralSync._

#### 📄 [rag_mcp_server.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/mcp_servers/rag_mcp_server.py)
- **Ruta Completa:** `agency/agents/mcp_servers/rag_mcp_server.py`
- **Líneas de Código:** 84
- **Descripción:** _rag_mcp_server.py_
- **Funciones Principales:** `simple_embedding, query_rag_knowledge`

#### 📄 [searxng_mcp_server.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/mcp_servers/searxng_mcp_server.py)
- **Ruta Completa:** `agency/agents/mcp_servers/searxng_mcp_server.py`
- **Líneas de Código:** 79
- **Descripción:** _searxng_mcp_server.py_
- **Funciones Principales:** `sanitize_html_content, searxng_search_sanitized`

#### 📄 [video_gen_client.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/mcp_servers/video_gen_client.py)
- **Ruta Completa:** `agency/agents/mcp_servers/video_gen_client.py`
- **Líneas de Código:** 148
- **Descripción:** _video_gen_client.py_
- **Clases / Entidades:** `ShotstackClient, VideoGenerationClient`
- **Funciones Principales:** `generate_storyboard_videos, __init__, create_edit_template, submit_render, generate_scene_video, _generate_shotstack_clip, _generate_fal_ai, _generate_google_veo, _generate_zsky, _generate_mock`

#### 📄 [lead_qualifier.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/qualifier/lead_qualifier.py)
- **Ruta Completa:** `agency/agents/qualifier/lead_qualifier.py`
- **Líneas de Código:** 49
- **Descripción:** _agents/qualifier/lead_qualifier.py_
- **Clases / Entidades:** `QualifiedMatch`
- **Funciones Principales:** `qualify_lead`

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/__init__.py)
- **Ruta Completa:** `agency/agents/nodes/__init__.py`
- **Líneas de Código:** 2

#### 📄 [dm_response.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/dm_response.py)
- **Ruta Completa:** `agency/agents/nodes/dm_response.py`
- **Líneas de Código:** 100
- **Descripción:** _dm_response.py_
- **Clases / Entidades:** `DMState`
- **Funciones Principales:** `classify_intent, generate_grounded_reply, node_dm_response`

#### 📄 [human_approval.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/human_approval.py)
- **Ruta Completa:** `agency/agents/nodes/human_approval.py`
- **Líneas de Código:** 39
- **Descripción:** _human_approval.py_
- **Funciones Principales:** `node_human_approval_idea, node_human_approval_publish`

#### 📄 [ideation.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/ideation.py)
- **Ruta Completa:** `agency/agents/nodes/ideation.py`
- **Líneas de Código:** 33
- **Descripción:** _ideation.py_
- **Funciones Principales:** `node_ideation`

#### 📄 [market_rum.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/market_rum.py)
- **Ruta Completa:** `agency/agents/nodes/market_rum.py`
- **Líneas de Código:** 40
- **Descripción:** _agents/nodes/market_rum.py_
- **Funciones Principales:** `get_dynamic_threshold`

#### 📄 [publish.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/publish.py)
- **Ruta Completa:** `agency/agents/nodes/publish.py`
- **Líneas de Código:** 27
- **Descripción:** _publish.py_
- **Funciones Principales:** `node_publish`

#### 📄 [scriptwriting.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/scriptwriting.py)
- **Ruta Completa:** `agency/agents/nodes/scriptwriting.py`
- **Líneas de Código:** 31
- **Descripción:** _scriptwriting.py_
- **Funciones Principales:** `node_scriptwriting`

#### 📄 [video_edit.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/nodes/video_edit.py)
- **Ruta Completa:** `agency/agents/nodes/video_edit.py`
- **Líneas de Código:** 41
- **Descripción:** _video_edit.py_
- **Funciones Principales:** `node_video_edit`

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/crews/__init__.py)
- **Ruta Completa:** `agency/agents/crews/__init__.py`
- **Líneas de Código:** 9
- **Descripción:** _Módulo de Crews Creativas (CrewAI) de ViralSync._

#### 📄 [ideation_crew.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/crews/ideation_crew.py)
- **Ruta Completa:** `agency/agents/crews/ideation_crew.py`
- **Líneas de Código:** 76
- **Descripción:** _ideation_crew.py_
- **Funciones Principales:** `run_ideation_crew`

#### 📄 [scriptwriting_crew.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/crews/scriptwriting_crew.py)
- **Ruta Completa:** `agency/agents/crews/scriptwriting_crew.py`
- **Líneas de Código:** 54
- **Descripción:** _scriptwriting_crew.py_
- **Funciones Principales:** `run_scriptwriting_crew`

#### 📄 [video_director_crew.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/crews/video_director_crew.py)
- **Ruta Completa:** `agency/agents/crews/video_director_crew.py`
- **Líneas de Código:** 161
- **Descripción:** _video_director_crew.py_
- **Funciones Principales:** `evaluate_script_quality, curate_video_metadata, extract_keywords_from_script, run_video_director_crew`

#### 📄 [video_prompt_crew.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/crews/video_prompt_crew.py)
- **Ruta Completa:** `agency/agents/crews/video_prompt_crew.py`
- **Líneas de Código:** 101
- **Descripción:** _video_prompt_crew.py_
- **Funciones Principales:** `run_video_prompt_crew`

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/criterion/__init__.py)
- **Ruta Completa:** `agency/agents/criterion/__init__.py`
- **Líneas de Código:** 15
- **Descripción:** _Módulo de Criterio Puro de ViralSync._

#### 📄 [filter_5_50.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/criterion/filter_5_50.py)
- **Ruta Completa:** `agency/agents/criterion/filter_5_50.py`
- **Líneas de Código:** 20
- **Descripción:** _filter_5_50.py_
- **Funciones Principales:** `passes_5_50_filter`

#### 📄 [niche_classifier.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/criterion/niche_classifier.py)
- **Ruta Completa:** `agency/agents/criterion/niche_classifier.py`
- **Líneas de Código:** 51
- **Descripción:** _niche_classifier.py_
- **Funciones Principales:** `classify_business_type`

#### 📄 [ppp_validator.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/criterion/ppp_validator.py)
- **Ruta Completa:** `agency/agents/criterion/ppp_validator.py`
- **Líneas de Código:** 67
- **Descripción:** _ppp_validator.py_
- **Funciones Principales:** `validate_ppp_structure`

#### 📄 [rum_calculator.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/agents/criterion/rum_calculator.py)
- **Ruta Completa:** `agency/agents/criterion/rum_calculator.py`
- **Líneas de Código:** 84
- **Descripción:** _rum_calculator.py_
- **Funciones Principales:** `calculate_rum_score, evaluate_rum_threshold, get_dynamic_threshold`

### 📂 `agency/backend/` (18 archivos, 1,199 líneas)

#### 📄 [main.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/main.py)
- **Ruta Completa:** `agency/backend/main.py`
- **Líneas de Código:** 124
- **Descripción:** _main.py_
- **Funciones Principales:** `sse_endpoint, verify_instagram_webhook, receive_instagram_webhook, event_generator`

#### 📄 [sse_manager.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/sse_manager.py)
- **Ruta Completa:** `agency/backend/sse_manager.py`
- **Líneas de Código:** 128
- **Descripción:** _sse_manager.py_
- **Clases / Entidades:** `SSEManager`
- **Funciones Principales:** `_format_sse, _event_generator, stream_tenant_events, emit_node_progress, __init__, subscribe, unsubscribe, broadcast, publish, _publish`

#### 📄 [graph_execution.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/routers/graph_execution.py)
- **Ruta Completa:** `agency/backend/routers/graph_execution.py`
- **Líneas de Código:** 82
- **Descripción:** _graph_execution.py_
- **Clases / Entidades:** `GraphRunRequest, ProgressReportRequest`
- **Funciones Principales:** `report_progress, run_graph`

#### 📄 [health.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/routers/health.py)
- **Ruta Completa:** `agency/backend/routers/health.py`
- **Líneas de Código:** 56
- **Descripción:** _health.py_
- **Clases / Entidades:** `HealthStatusResponse`
- **Funciones Principales:** `unified_health_check`

#### 📄 [ingestion.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/routers/ingestion.py)
- **Ruta Completa:** `agency/backend/routers/ingestion.py`
- **Líneas de Código:** 71
- **Descripción:** _ingestion.py_
- **Clases / Entidades:** `TenantCreateRequest`
- **Funciones Principales:** `create_tenant, ingest_product_data`

#### 📄 [leads.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/routers/leads.py)
- **Ruta Completa:** `agency/backend/routers/leads.py`
- **Líneas de Código:** 54
- **Descripción:** _leads.py_
- **Clases / Entidades:** `TakeoverRequest`
- **Funciones Principales:** `get_tenant_leads, takeover_lead`

#### 📄 [metrics.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/routers/metrics.py)
- **Ruta Completa:** `agency/backend/routers/metrics.py`
- **Líneas de Código:** 59
- **Descripción:** _metrics.py_
- **Funciones Principales:** `get_metrics, get_metrics_72h`

#### 📄 [minio_client.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/storage/minio_client.py)
- **Ruta Completa:** `agency/backend/storage/minio_client.py`
- **Líneas de Código:** 48
- **Descripción:** _minio_client.py_
- **Clases / Entidades:** `MinIOStorageClient`
- **Funciones Principales:** `save_product_photo_to_minio, __init__, upload_product_image`

#### 📄 [models.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/db/models.py)
- **Ruta Completa:** `agency/backend/db/models.py`
- **Líneas de Código:** 108
- **Descripción:** _models.py_
- **Clases / Entidades:** `Base, Tenant, Product, Idea, Script, Post, Lead, LLMUsageLog, AuditLog`

#### 📄 [session.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/db/session.py)
- **Ruta Completa:** `agency/backend/db/session.py`
- **Líneas de Código:** 46
- **Descripción:** _session.py_
- **Funciones Principales:** `init_db, get_async_db`

#### 📄 [llm_budget_service.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/services/llm_budget_service.py)
- **Ruta Completa:** `agency/backend/services/llm_budget_service.py`
- **Líneas de Código:** 73
- **Descripción:** _llm_budget_service.py_
- **Funciones Principales:** `calculate_llm_cost, track_llm_token_usage, check_tenant_llm_budget`

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/webhooks/__init__.py)
- **Ruta Completa:** `agency/backend/webhooks/__init__.py`
- **Líneas de Código:** 7
- **Descripción:** _Módulo de Webhooks Inbound de Meta / Instagram Graph API._

#### 📄 [instagram_inbound.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/webhooks/instagram_inbound.py)
- **Ruta Completa:** `agency/backend/webhooks/instagram_inbound.py`
- **Líneas de Código:** 61
- **Descripción:** _instagram_inbound.py_
- **Funciones Principales:** `process_instagram_webhook_payload`

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/security/__init__.py)
- **Ruta Completa:** `agency/backend/security/__init__.py`
- **Líneas de Código:** 8
- **Descripción:** _Módulo de Seguridad Backend de ViralSync._

#### 📄 [audit_logger.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/security/audit_logger.py)
- **Ruta Completa:** `agency/backend/security/audit_logger.py`
- **Líneas de Código:** 28
- **Descripción:** _audit_logger.py_
- **Funciones Principales:** `log_audit_event`

#### 📄 [auth.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/security/auth.py)
- **Ruta Completa:** `agency/backend/security/auth.py`
- **Líneas de Código:** 133
- **Descripción:** _auth.py_
- **Clases / Entidades:** `TenantContextMiddleware`
- **Funciones Principales:** `_base64url_encode, _base64url_decode, create_access_token, decode_access_token, get_current_user, require_roles, role_checker, dispatch`

#### 📄 [hmac_validator.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/security/hmac_validator.py)
- **Ruta Completa:** `agency/backend/security/hmac_validator.py`
- **Líneas de Código:** 37
- **Descripción:** _hmac_validator.py_
- **Funciones Principales:** `verify_meta_hmac_signature`

#### 📄 [rag_cache.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/backend/cache/rag_cache.py)
- **Ruta Completa:** `agency/backend/cache/rag_cache.py`
- **Líneas de Código:** 76
- **Descripción:** _rag_cache.py_
- **Clases / Entidades:** `RAGSemanticCache`
- **Funciones Principales:** `__init__, _get_redis_client, _hash_query, get, set`

### 📂 `agency/frontend/` (42 archivos, 4,117 líneas)

#### 📄 [jsconfig.json](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/jsconfig.json)
- **Ruta Completa:** `agency/frontend/jsconfig.json`
- **Líneas de Código:** 8

#### 📄 [next.config.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/next.config.js)
- **Ruta Completa:** `agency/frontend/next.config.js`
- **Líneas de Código:** 6

#### 📄 [package-lock.json](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/package-lock.json)
- **Ruta Completa:** `agency/frontend/package-lock.json`
- **Líneas de Código:** 2148

#### 📄 [package.json](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/package.json)
- **Ruta Completa:** `agency/frontend/package.json`
- **Líneas de Código:** 27

#### 📄 [postcss.config.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/postcss.config.js)
- **Ruta Completa:** `agency/frontend/postcss.config.js`
- **Líneas de Código:** 6

#### 📄 [tailwind.config.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/tailwind.config.js)
- **Ruta Completa:** `agency/frontend/tailwind.config.js`
- **Líneas de Código:** 28

#### 📄 [middleware.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/middleware.js)
- **Ruta Completa:** `agency/frontend/src/middleware.js`
- **Líneas de Código:** 27
- **Componentes Exportados:** `middleware, config`

#### 📄 [index.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/index.js)
- **Ruta Completa:** `agency/frontend/src/features/index.js`
- **Líneas de Código:** 9

#### 📄 [PublishApprovalView.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/VideoPreview/views/PublishApprovalView.jsx)
- **Ruta Completa:** `agency/frontend/src/features/VideoPreview/views/PublishApprovalView.jsx`
- **Líneas de Código:** 71
- **Componentes Exportados:** `PublishApprovalView`

#### 📄 [MetricsDashboardView.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/Metrics72h/views/MetricsDashboardView.jsx)
- **Ruta Completa:** `agency/frontend/src/features/Metrics72h/views/MetricsDashboardView.jsx`
- **Líneas de Código:** 62
- **Componentes Exportados:** `MetricsDashboardView`

#### 📄 [MetricClassificationCard.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/Metrics72h/components/MetricClassificationCard.jsx)
- **Ruta Completa:** `agency/frontend/src/features/Metrics72h/components/MetricClassificationCard.jsx`
- **Líneas de Código:** 48
- **Componentes Exportados:** `MetricClassificationCard`

#### 📄 [PipelineMonitorView.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/Pipeline/views/PipelineMonitorView.jsx)
- **Ruta Completa:** `agency/frontend/src/features/Pipeline/views/PipelineMonitorView.jsx`
- **Líneas de Código:** 90
- **Componentes Exportados:** `PipelineMonitorView`

#### 📄 [ScriptInspectorView.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/Scriptwriting/views/ScriptInspectorView.jsx)
- **Ruta Completa:** `agency/frontend/src/features/Scriptwriting/views/ScriptInspectorView.jsx`
- **Líneas de Código:** 44
- **Componentes Exportados:** `ScriptInspectorView`

#### 📄 [Script4BlockReader.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/Scriptwriting/components/Script4BlockReader.jsx)
- **Ruta Completa:** `agency/frontend/src/features/Scriptwriting/components/Script4BlockReader.jsx`
- **Líneas de Código:** 28
- **Componentes Exportados:** `Script4BlockReader`

#### 📄 [InboundLeadsView.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/LeadsInbound/views/InboundLeadsView.jsx)
- **Ruta Completa:** `agency/frontend/src/features/LeadsInbound/views/InboundLeadsView.jsx`
- **Líneas de Código:** 71
- **Componentes Exportados:** `InboundLeadsView`

#### 📄 [LeadsTable.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/LeadsInbound/components/LeadsTable.jsx)
- **Ruta Completa:** `agency/frontend/src/features/LeadsInbound/components/LeadsTable.jsx`
- **Líneas de Código:** 53
- **Componentes Exportados:** `LeadsTable`

#### 📄 [IdeaApprovalView.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/Ideation/views/IdeaApprovalView.jsx)
- **Ruta Completa:** `agency/frontend/src/features/Ideation/views/IdeaApprovalView.jsx`
- **Líneas de Código:** 95
- **Componentes Exportados:** `IdeaApprovalView`

#### 📄 [RUMBreakdownBarChart.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/Ideation/components/RUMBreakdownBarChart.jsx)
- **Ruta Completa:** `agency/frontend/src/features/Ideation/components/RUMBreakdownBarChart.jsx`
- **Líneas de Código:** 35
- **Componentes Exportados:** `RUMBreakdownBarChart`

#### 📄 [BrainManagementView.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/features/RAGBrain/views/BrainManagementView.jsx)
- **Ruta Completa:** `agency/frontend/src/features/RAGBrain/views/BrainManagementView.jsx`
- **Líneas de Código:** 62
- **Componentes Exportados:** `BrainManagementView`

#### 📄 [useAgentStore.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/stores/useAgentStore.js)
- **Ruta Completa:** `agency/frontend/src/stores/useAgentStore.js`
- **Líneas de Código:** 38
- **Componentes Exportados:** `useAgentStore`

#### 📄 [useTenantStore.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/stores/useTenantStore.js)
- **Ruta Completa:** `agency/frontend/src/stores/useTenantStore.js`
- **Líneas de Código:** 30
- **Componentes Exportados:** `useTenantStore`

#### 📄 [useSSEStream.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/hooks/useSSEStream.js)
- **Ruta Completa:** `agency/frontend/src/hooks/useSSEStream.js`
- **Líneas de Código:** 77
- **Componentes Exportados:** `useSSEStream`

#### 📄 [error.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/error.js)
- **Ruta Completa:** `agency/frontend/src/app/error.js`
- **Líneas de Código:** 24
- **Componentes Exportados:** `Error`

#### 📄 [global-error.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/global-error.js)
- **Ruta Completa:** `agency/frontend/src/app/global-error.js`
- **Líneas de Código:** 28
- **Componentes Exportados:** `GlobalError`

#### 📄 [globals.css](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/globals.css)
- **Ruta Completa:** `agency/frontend/src/app/globals.css`
- **Líneas de Código:** 65

#### 📄 [layout.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/layout.js)
- **Ruta Completa:** `agency/frontend/src/app/layout.js`
- **Líneas de Código:** 16
- **Componentes Exportados:** `metadata, RootLayout`

#### 📄 [loading.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/loading.js)
- **Ruta Completa:** `agency/frontend/src/app/loading.js`
- **Líneas de Código:** 7
- **Componentes Exportados:** `Loading`

#### 📄 [not-found.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/not-found.js)
- **Ruta Completa:** `agency/frontend/src/app/not-found.js`
- **Líneas de Código:** 19
- **Componentes Exportados:** `NotFound`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/page.js)
- **Ruta Completa:** `agency/frontend/src/app/page.js`
- **Líneas de Código:** 351
- **Componentes Exportados:** `DashboardPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/[tenantId]/cerebro/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/[tenantId]/cerebro/page.js`
- **Líneas de Código:** 9
- **Componentes Exportados:** `CerebroPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/[tenantId]/metricas/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/[tenantId]/metricas/page.js`
- **Líneas de Código:** 9
- **Componentes Exportados:** `MetricasPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/[tenantId]/pipeline/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/[tenantId]/pipeline/page.js`
- **Líneas de Código:** 9
- **Componentes Exportados:** `PipelinePage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/[tenantId]/leads/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/[tenantId]/leads/page.js`
- **Líneas de Código:** 9
- **Componentes Exportados:** `LeadsPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/[tenantId]/guiones/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/[tenantId]/guiones/page.js`
- **Líneas de Código:** 9
- **Componentes Exportados:** `GuionesPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/[tenantId]/aprobaciones/ideas/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/[tenantId]/aprobaciones/ideas/page.js`
- **Líneas de Código:** 9
- **Componentes Exportados:** `IdeasPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/[tenantId]/aprobaciones/publicacion/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/[tenantId]/aprobaciones/publicacion/page.js`
- **Líneas de Código:** 9
- **Componentes Exportados:** `PublicacionPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/tenants/nuevo/page.js)
- **Ruta Completa:** `agency/frontend/src/app/tenants/nuevo/page.js`
- **Líneas de Código:** 112
- **Componentes Exportados:** `NuevoTenantPage`

#### 📄 [page.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/app/admin/sistema/page.js)
- **Ruta Completa:** `agency/frontend/src/app/admin/sistema/page.js`
- **Líneas de Código:** 54
- **Componentes Exportados:** `AdminSistemaPage`

#### 📄 [apiConfig.js](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/services/apiConfig.js)
- **Ruta Completa:** `agency/frontend/src/services/apiConfig.js`
- **Líneas de Código:** 23

#### 📄 [ProductIngestModal.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/components/ProductIngestModal.jsx)
- **Ruta Completa:** `agency/frontend/src/components/ProductIngestModal.jsx`
- **Líneas de Código:** 178
- **Componentes Exportados:** `ProductIngestModal`

#### 📄 [Header.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/components/layout/Header.jsx)
- **Ruta Completa:** `agency/frontend/src/components/layout/Header.jsx`
- **Líneas de Código:** 54
- **Componentes Exportados:** `Header`

#### 📄 [Sidebar.jsx](file:///home/ivan/Desktop/AgentMarketingIA/agency/frontend/src/components/layout/Sidebar.jsx)
- **Ruta Completa:** `agency/frontend/src/components/layout/Sidebar.jsx`
- **Líneas de Código:** 60
- **Componentes Exportados:** `Sidebar`

### 📂 `agency/gateway/` (3 archivos, 112 líneas)

#### 📄 [litellm_config.dev.yaml](file:///home/ivan/Desktop/AgentMarketingIA/agency/gateway/litellm_config.dev.yaml)
- **Ruta Completa:** `agency/gateway/litellm_config.dev.yaml`
- **Líneas de Código:** 24

#### 📄 [litellm_config.production.yaml](file:///home/ivan/Desktop/AgentMarketingIA/agency/gateway/litellm_config.production.yaml)
- **Ruta Completa:** `agency/gateway/litellm_config.production.yaml`
- **Líneas de Código:** 42

#### 📄 [litellm_config.staging.yaml](file:///home/ivan/Desktop/AgentMarketingIA/agency/gateway/litellm_config.staging.yaml)
- **Ruta Completa:** `agency/gateway/litellm_config.staging.yaml`
- **Líneas de Código:** 46

### 📂 `agency/knowledge/` (10 archivos, 168 líneas)

#### 📄 [brand_character.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/brand_character.md)
- **Ruta Completa:** `agency/knowledge/brand_character.md`
- **Líneas de Código:** 9

#### 📄 [classification_80_20.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/classification_80_20.md)
- **Ruta Completa:** `agency/knowledge/classification_80_20.md`
- **Líneas de Código:** 11

#### 📄 [competitor_quadrants.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/competitor_quadrants.md)
- **Ruta Completa:** `agency/knowledge/competitor_quadrants.md`
- **Líneas de Código:** 10

#### 📄 [filter_5_50.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/filter_5_50.md)
- **Ruta Completa:** `agency/knowledge/filter_5_50.md`
- **Líneas de Código:** 10

#### 📄 [inbound_funnel.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/inbound_funnel.md)
- **Ruta Completa:** `agency/knowledge/inbound_funnel.md`
- **Líneas de Código:** 7

#### 📄 [ingest_knowledge.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/ingest_knowledge.py)
- **Ruta Completa:** `agency/knowledge/ingest_knowledge.py`
- **Líneas de Código:** 68
- **Descripción:** _ingest_knowledge.py_
- **Funciones Principales:** `simple_embedding, run_ingestion`

#### 📄 [pdh_triangle.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/pdh_triangle.md)
- **Ruta Completa:** `agency/knowledge/pdh_triangle.md`
- **Líneas de Código:** 9

#### 📄 [ppp_promise.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/ppp_promise.md)
- **Ruta Completa:** `agency/knowledge/ppp_promise.md`
- **Líneas de Código:** 10

#### 📄 [rum_formula.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/rum_formula.md)
- **Ruta Completa:** `agency/knowledge/rum_formula.md`
- **Líneas de Código:** 20

#### 📄 [script_4_blocks.md](file:///home/ivan/Desktop/AgentMarketingIA/agency/knowledge/script_4_blocks.md)
- **Ruta Completa:** `agency/knowledge/script_4_blocks.md`
- **Líneas de Código:** 14

### 📂 `agency/microservices/` (7 archivos, 471 líneas)

#### 📄 [Dockerfile](file:///home/ivan/Desktop/AgentMarketingIA/agency/microservices/renderer/Dockerfile)
- **Ruta Completa:** `agency/microservices/renderer/Dockerfile`
- **Líneas de Código:** 18

#### 📄 [app.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/microservices/renderer/app.py)
- **Ruta Completa:** `agency/microservices/renderer/app.py`
- **Líneas de Código:** 242
- **Descripción:** _app.py_
- **Clases / Entidades:** `RenderRequest, RenderResponse`
- **Funciones Principales:** `generate_speech_audio, download_pexels_videos, compose_video_moviepy, upload_to_minio, report_render_progress, render_video_endpoint, health_check`

#### 📄 [requirements.txt](file:///home/ivan/Desktop/AgentMarketingIA/agency/microservices/renderer/requirements.txt)
- **Ruta Completa:** `agency/microservices/renderer/requirements.txt`
- **Líneas de Código:** 8

#### 📄 [Dockerfile](file:///home/ivan/Desktop/AgentMarketingIA/agency/microservices/publisher/Dockerfile)
- **Ruta Completa:** `agency/microservices/publisher/Dockerfile`
- **Líneas de Código:** 12

#### 📄 [adapters.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/microservices/publisher/adapters.py)
- **Ruta Completa:** `agency/microservices/publisher/adapters.py`
- **Líneas de Código:** 116
- **Descripción:** _adapters.py_
- **Clases / Entidades:** `BaseSocialPublisher, InstagramGraphPublisher, TikTokPublisher, YouTubeShortsPublisher, PublisherFactory`
- **Funciones Principales:** `publish_reel, get_publisher`

#### 📄 [app.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/microservices/publisher/app.py)
- **Ruta Completa:** `agency/microservices/publisher/app.py`
- **Líneas de Código:** 70
- **Descripción:** _app.py_
- **Clases / Entidades:** `PublishRequest, PublishResponse`
- **Funciones Principales:** `publish_video_endpoint, health_check`

#### 📄 [requirements.txt](file:///home/ivan/Desktop/AgentMarketingIA/agency/microservices/publisher/requirements.txt)
- **Ruta Completa:** `agency/microservices/publisher/requirements.txt`
- **Líneas de Código:** 5

### 📂 `agency/migrations/` (1 archivos, 202 líneas)

#### 📄 [001_init_schema.sql](file:///home/ivan/Desktop/AgentMarketingIA/agency/migrations/001_init_schema.sql)
- **Ruta Completa:** `agency/migrations/001_init_schema.sql`
- **Líneas de Código:** 202

### 📂 `agency/tests/` (32 archivos, 1,557 líneas)

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/__init__.py)
- **Ruta Completa:** `agency/tests/__init__.py`
- **Líneas de Código:** 1

#### 📄 [conftest.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/conftest.py)
- **Ruta Completa:** `agency/tests/conftest.py`
- **Líneas de Código:** 17
- **Descripción:** _conftest.py_
- **Funciones Principales:** `set_testing_env`

#### 📄 [test_audit_findings_resolutions.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_audit_findings_resolutions.py)
- **Ruta Completa:** `agency/tests/unit/test_audit_findings_resolutions.py`
- **Líneas de Código:** 64
- **Descripción:** _test_audit_findings_resolutions.py_
- **Funciones Principales:** `test_duplicated_sse_manager_removed, test_publisher_adapter_factory, test_publisher_adapter_execution, test_llm_budget_atomic_tracking`

#### 📄 [test_audit_second_pass_resolutions.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_audit_second_pass_resolutions.py)
- **Ruta Completa:** `agency/tests/unit/test_audit_second_pass_resolutions.py`
- **Líneas de Código:** 82
- **Descripción:** _test_audit_second_pass_resolutions.py_
- **Funciones Principales:** `test_celery_acks_late_configuration, test_dm_intent_classification, test_dm_grounded_reply_confidence, test_dm_graph_routing, test_dm_graph_compilation_and_execution, test_rum_ema_recalibration_and_clamp`

#### 📄 [test_brechas_consolidation.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_brechas_consolidation.py)
- **Ruta Completa:** `agency/tests/unit/test_brechas_consolidation.py`
- **Líneas de Código:** 64
- **Descripción:** _test_brechas_consolidation.py_
- **Funciones Principales:** `test_shotstack_client_template_creation, test_rag_semantic_cache_hit, test_webhook_dlq_retry_processing`

#### 📄 [test_celery_tasks.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_celery_tasks.py)
- **Ruta Completa:** `agency/tests/unit/test_celery_tasks.py`
- **Líneas de Código:** 40
- **Descripción:** _test_celery_tasks.py_
- **Funciones Principales:** `test_video_edit_task_eager_execution, test_metrics_loop_task_verde, test_metrics_loop_task_rojo`

#### 📄 [test_ci_config.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_ci_config.py)
- **Ruta Completa:** `agency/tests/unit/test_ci_config.py`
- **Líneas de Código:** 89
- **Descripción:** _Contract tests for the Phase-0 slice-2 CI/CD configuration._
- **Funciones Principales:** `_ruff_toml, _ci_workflow, test_ruff_toml_sets_line_length_120, test_ruff_toml_targets_python_312, test_ruff_toml_selects_expected_rule_codes, test_ci_workflow_triggers_on_push_and_pull_request, test_ci_workflow_defines_four_gating_jobs, test_ci_python_job_installs_lock_and_runs_coverage_gate, test_ci_python_job_lints_and_audits, test_ci_frontend_job_builds_and_audits ... (+3 más)`

#### 📄 [test_deps_prune.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_deps_prune.py)
- **Ruta Completa:** `agency/tests/unit/test_deps_prune.py`
- **Líneas de Código:** 120
- **Descripción:** _Slice 1 (python-deps) — prune verification tests._
- **Funciones Principales:** `_declared_name, _parse_names, _requirements_txt, _requirements_lock, test_pruned_packages_absent_from_requirements_txt, test_pruned_packages_absent_from_lockfile, test_sqlalchemy_only_reintroduced_as_alembic_transitive_dep, test_kept_dependency_declared_with_pin`

#### 📄 [test_e2e_full_pipeline_and_garbage_collection.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_e2e_full_pipeline_and_garbage_collection.py)
- **Ruta Completa:** `agency/tests/unit/test_e2e_full_pipeline_and_garbage_collection.py`
- **Líneas de Código:** 73
- **Descripción:** _test_e2e_full_pipeline_and_garbage_collection.py_
- **Funciones Principales:** `test_celery_task_routing_configuration, test_trend_scraper_task_execution, test_garbage_collection_zero_waste_policy, test_e2e_full_state_graph_pipeline`

#### 📄 [test_enterprise_phases_0_to_5.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_enterprise_phases_0_to_5.py)
- **Ruta Completa:** `agency/tests/unit/test_enterprise_phases_0_to_5.py`
- **Líneas de Código:** 94
- **Descripción:** _test_enterprise_phases_0_to_5.py_
- **Funciones Principales:** `test_fase_0_unified_health_check_endpoint, test_fase_1_jwt_auth_and_rbac, test_fase_2_modular_routers_ingestion_and_leads, test_fase_4_llm_cost_calculation_and_budget, test_fase_5_audit_logging`

#### 📄 [test_fastapi_endpoints.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_fastapi_endpoints.py)
- **Ruta Completa:** `agency/tests/unit/test_fastapi_endpoints.py`
- **Líneas de Código:** 55
- **Descripción:** _test_fastapi_endpoints.py_
- **Funciones Principales:** `test_create_tenant_endpoint, test_get_metrics_endpoint, test_takeover_lead_endpoint`

#### 📄 [test_filter_5_50.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_filter_5_50.py)
- **Ruta Completa:** `agency/tests/unit/test_filter_5_50.py`
- **Líneas de Código:** 30
- **Descripción:** _test_filter_5_50.py_
- **Funciones Principales:** `test_passes_5_50_filter_both_true, test_passes_5_50_filter_one_false, test_passes_5_50_filter_missing_keys`

#### 📄 [test_frontend_features_phase10.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_frontend_features_phase10.py)
- **Ruta Completa:** `agency/tests/unit/test_frontend_features_phase10.py`
- **Líneas de Código:** 23
- **Descripción:** _test_frontend_features_phase10.py_
- **Funciones Principales:** `test_phase10_feature_files_exist`

#### 📄 [test_frontend_features_phase11.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_frontend_features_phase11.py)
- **Ruta Completa:** `agency/tests/unit/test_frontend_features_phase11.py`
- **Líneas de Código:** 23
- **Descripción:** _test_frontend_features_phase11.py_
- **Funciones Principales:** `test_phase11_and_frontend_completion_files_exist`

#### 📄 [test_frontend_features_phase9.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_frontend_features_phase9.py)
- **Ruta Completa:** `agency/tests/unit/test_frontend_features_phase9.py`
- **Líneas de Código:** 23
- **Descripción:** _test_frontend_features_phase9.py_
- **Funciones Principales:** `test_phase9_feature_files_exist`

#### 📄 [test_frontend_infra.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_frontend_infra.py)
- **Ruta Completa:** `agency/tests/unit/test_frontend_infra.py`
- **Líneas de Código:** 68
- **Descripción:** _test_frontend_infra.py_
- **Funciones Principales:** `test_frontend_infra_files_exist, test_frontend_boundary_files_exist, test_package_json_pins, test_jsconfig_alias_resolves`

#### 📄 [test_frontend_structure.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_frontend_structure.py)
- **Ruta Completa:** `agency/tests/unit/test_frontend_structure.py`
- **Líneas de Código:** 21
- **Descripción:** _test_frontend_structure.py_
- **Funciones Principales:** `test_frontend_files_exist`

#### 📄 [test_graph_state.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_graph_state.py)
- **Ruta Completa:** `agency/tests/unit/test_graph_state.py`
- **Líneas de Código:** 23
- **Descripción:** _test_graph_state.py_
- **Funciones Principales:** `test_build_agency_graph_compiles, test_agency_state_initialization`

#### 📄 [test_hmac_validator.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_hmac_validator.py)
- **Ruta Completa:** `agency/tests/unit/test_hmac_validator.py`
- **Líneas de Código:** 56
- **Descripción:** _test_hmac_validator.py_
- **Funciones Principales:** `test_verify_meta_hmac_signature_valid, test_verify_meta_hmac_signature_invalid_secret, test_verify_meta_hmac_signature_tampered_payload, test_verify_meta_hmac_signature_malformed_header`

#### 📄 [test_ideation_crew.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_ideation_crew.py)
- **Ruta Completa:** `agency/tests/unit/test_ideation_crew.py`
- **Líneas de Código:** 27
- **Descripción:** _test_ideation_crew.py_
- **Funciones Principales:** `test_run_ideation_crew_structure`

#### 📄 [test_ingest_knowledge.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_ingest_knowledge.py)
- **Ruta Completa:** `agency/tests/unit/test_ingest_knowledge.py`
- **Líneas de Código:** 23
- **Descripción:** _test_ingest_knowledge.py_
- **Funciones Principales:** `test_knowledge_markdown_files_exist, test_simple_embedding_consistency`

#### 📄 [test_minio_and_classifier.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_minio_and_classifier.py)
- **Ruta Completa:** `agency/tests/unit/test_minio_and_classifier.py`
- **Líneas de Código:** 32
- **Descripción:** _test_minio_and_classifier.py_
- **Funciones Principales:** `test_classify_business_type_product, test_classify_business_type_service, test_minio_storage_client_upload`

#### 📄 [test_ppp_validator.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_ppp_validator.py)
- **Ruta Completa:** `agency/tests/unit/test_ppp_validator.py`
- **Líneas de Código:** 36
- **Descripción:** _test_ppp_validator.py_
- **Funciones Principales:** `test_validate_ppp_valid, test_validate_ppp_missing_timeframe, test_validate_ppp_missing_objection, test_validate_ppp_too_long`

#### 📄 [test_rag_mcp.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_rag_mcp.py)
- **Ruta Completa:** `agency/tests/unit/test_rag_mcp.py`
- **Líneas de Código:** 26
- **Descripción:** _test_rag_mcp.py_
- **Funciones Principales:** `test_simple_embedding_length_and_range, test_query_rag_knowledge_fallback_when_offline`

#### 📄 [test_rum_calculator.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_rum_calculator.py)
- **Ruta Completa:** `agency/tests/unit/test_rum_calculator.py`
- **Líneas de Código:** 67
- **Descripción:** _test_rum_calculator.py_
- **Funciones Principales:** `test_calculate_rum_score_valid, test_calculate_rum_score_out_of_bounds, test_calculate_rum_score_missing_key, test_evaluate_rum_threshold_pass, test_evaluate_rum_threshold_fail`

#### 📄 [test_scriptwriting_crew.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_scriptwriting_crew.py)
- **Ruta Completa:** `agency/tests/unit/test_scriptwriting_crew.py`
- **Líneas de Código:** 26
- **Descripción:** _test_scriptwriting_crew.py_
- **Funciones Principales:** `test_run_scriptwriting_crew_4_blocks`

#### 📄 [test_searxng_mcp.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_searxng_mcp.py)
- **Ruta Completa:** `agency/tests/unit/test_searxng_mcp.py`
- **Líneas de Código:** 51
- **Descripción:** _test_searxng_mcp.py_
- **Funciones Principales:** `test_sanitize_html_content_strips_tags, test_searxng_search_sanitized_fallback_when_offline, test_searxng_search_sanitized_mock_http`

#### 📄 [test_video_director_guardian.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_video_director_guardian.py)
- **Ruta Completa:** `agency/tests/unit/test_video_director_guardian.py`
- **Líneas de Código:** 79
- **Descripción:** _test_video_director_guardian.py_
- **Funciones Principales:** `test_evaluate_script_quality_pass, test_evaluate_script_quality_fail, test_curate_video_metadata, test_video_director_hardware_filter_and_rejection`

#### 📄 [test_video_prompt_crew.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_video_prompt_crew.py)
- **Ruta Completa:** `agency/tests/unit/test_video_prompt_crew.py`
- **Líneas de Código:** 51
- **Descripción:** _test_video_prompt_crew.py_
- **Funciones Principales:** `test_video_prompt_crew_storyboard_generation, test_video_gen_client_mock_provider, test_generate_storyboard_videos`

#### 📄 [test_video_renderer_microservice.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/unit/test_video_renderer_microservice.py)
- **Ruta Completa:** `agency/tests/unit/test_video_renderer_microservice.py`
- **Líneas de Código:** 54
- **Descripción:** _test_video_renderer_microservice.py_
- **Funciones Principales:** `test_video_director_crew_payload_formatting, test_extract_keywords_from_script, test_trigger_video_render_task_fallback`

#### 📄 [__init__.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/e2e/__init__.py)
- **Ruta Completa:** `agency/tests/e2e/__init__.py`
- **Líneas de Código:** 1

#### 📄 [test_full_pipeline.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/tests/e2e/test_full_pipeline.py)
- **Ruta Completa:** `agency/tests/e2e/test_full_pipeline.py`
- **Líneas de Código:** 118
- **Descripción:** _test_full_pipeline.py_
- **Funciones Principales:** `test_complete_viral_sync_lifecycle`

### 📂 `agency/workers/` (5 archivos, 336 líneas)

#### 📄 [celery_app.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/workers/celery_app.py)
- **Ruta Completa:** `agency/workers/celery_app.py`
- **Líneas de Código:** 44
- **Descripción:** _celery_app.py_

#### 📄 [metrics_loop_task.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/workers/metrics_loop_task.py)
- **Ruta Completa:** `agency/workers/metrics_loop_task.py`
- **Líneas de Código:** 76
- **Descripción:** _metrics_loop_task.py_
- **Funciones Principales:** `update_niche_rum_threshold_ema, audit_72h_metrics`

#### 📄 [trend_scraper_task.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/workers/trend_scraper_task.py)
- **Ruta Completa:** `agency/workers/trend_scraper_task.py`
- **Líneas de Código:** 48
- **Descripción:** _trend_scraper_task.py_
- **Funciones Principales:** `scrape_daily_marketing_trends`

#### 📄 [video_edit_task.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/workers/video_edit_task.py)
- **Ruta Completa:** `agency/workers/video_edit_task.py`
- **Líneas de Código:** 124
- **Descripción:** _video_edit_task.py_
- **Funciones Principales:** `trigger_video_render, process_video_postproduction`

#### 📄 [webhook_dlq_task.py](file:///home/ivan/Desktop/AgentMarketingIA/agency/workers/webhook_dlq_task.py)
- **Ruta Completa:** `agency/workers/webhook_dlq_task.py`
- **Líneas de Código:** 44
- **Descripción:** _webhook_dlq_task.py_
- **Funciones Principales:** `process_failed_webhook_retry`
