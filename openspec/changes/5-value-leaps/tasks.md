# Tasks: 5-value-leaps

Orden de implementación: S1 (DM Leads CRM, PR #1) → S2 (Voice Personas, PR #2 en 2 batches: S2a backend / S2b frontend+render) → S3 (Auto-Publicación, PR #3) → S4 (Competitor Benchmark, PR #4) → S5 (PDF Reports, PR #5). TDD estricto en cada task (red → implementación → green). Migraciones 011–015 en orden de implementación, idempotentes (`IF NOT EXISTS`, patrón 002). Comando base: `cd agency && ../venv/bin/python -m pytest tests/`.

## S1 — DM Leads CRM (PR #1)

> **Estado**: 🔄 PR #28 abierto (2026-08-19), pendiente de CI/merge a `main` — histórico: los artifacts del slice declaraban "Archivado/entregado 2026-08-15", pero los commits vivían solo en las ramas `s1a1`/`s1a2`/`s1b` sin PR. Recuperado por cherry-pick de los 6 commits (`616bde7`..`951c4d3`) sobre `main` actual (con S2 ya integrado) + fix de lint heredado. Validado local: gate completo (383 passed con tests S1 incluidos) + ruff limpio.

### T-S1-01: Migración 011 — leads.qualification_score + DROP NOT NULL video_id
- **Descripción**: Crear `agency/migrations/011_leads_qualification.sql`: `ADD COLUMN IF NOT EXISTS qualification_score INTEGER NOT NULL DEFAULT 0`, `platform TEXT NOT NULL DEFAULT 'instagram'`, `dedup_hash TEXT`, `ALTER COLUMN video_id DROP NOT NULL` (el webhook no trae video), `CREATE UNIQUE INDEX uq_leads_dedup_hash` y `CREATE INDEX idx_leads_status`.
- **REQs**: REQ-DM-LEAD-02 (habilita 01/05)
- **Depende de**: —
- **Archivos**: `agency/migrations/011_leads_qualification.sql`
- **Criterios**: `pytest tests/unit/test_db_indexes.py` (extendido: migración 011 existe + columna/index declarados); aplicar migración sobre schema previo → `qualification_score` INTEGER + índice `status` presentes
- **Estimación**: ~35 líneas

### T-S1-02: Modelo Lead actualizado
- **Descripción**: En `agency/backend/db/models.py`, agregar a `Lead`: `qualification_score` (int, default 0), `platform` (default 'instagram'), `dedup_hash` (unique, nullable).
- **REQs**: REQ-DM-LEAD-02, REQ-DM-LEAD-01, REQ-DM-LEAD-05
- **Depende de**: T-S1-01
- **Archivos**: `agency/backend/db/models.py`
- **Criterios**: `pytest tests/unit/test_db_indexes.py` (RED: Lead declara `qualification_score` y unique `dedup_hash` → GREEN tras modelo)
- **Estimación**: ~10 líneas

### T-S1-03: Servicio de scoring puro
- **Descripción**: Crear `agency/backend/services/lead_scoring.py` con `score_lead(message: str, intent: str) -> tuple[int, str]` (0–100, `Nuevo`/`Contactado`/`Calificado`): `purchase_intent` + keyword precio/demo → ≥60 `Calificado`; `spam` o sin keywords → <30 `Nuevo`. Patrón `trend_scorer.py`, sin IO.
- **REQs**: REQ-DM-LEAD-03
- **Depende de**: —
- **Archivos**: `agency/backend/services/lead_scoring.py`, `agency/tests/unit/test_lead_scoring.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_lead_scoring.py` (high-intent ≥60/Calificado; spam <30/Nuevo) → GREEN
- **Estimación**: ~55 líneas (+ ~45 test)

### T-S1-04: Worker persist_instagram_lead
- **Descripción**: Crear `agency/workers/lead_persist_task.py` con `persist_instagram_lead(tenant_id, lead_data)`: 1) dedup `sha256(ig_user_id + "|" + mensaje)` → retorna existente si aplica; 2) INSERT `Lead(tenant_id, platform='instagram', status='Nuevo')`; 3) `score_lead` → update score+status; 4) best-effort `dm_graph` (`build_dm_graph()` con state mínimo) → intent/confidence JSON en `conversacion_history`, con fallback `classify_intent` si Qdrant/LLM fallan (try/except, nunca rompe persistencia). `node_send_dm_reply` NO se toca.
- **REQs**: REQ-DM-LEAD-01, REQ-DM-LEAD-04, REQ-DM-LEAD-05, REQ-DM-LEAD-06
- **Depende de**: T-S1-02, T-S1-03
- **Archivos**: `agency/workers/lead_persist_task.py`, `agency/tests/unit/test_lead_persist_task.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_lead_persist_task.py` (persistencia con tenant resuelto; webhook repetido no duplica; clasificación en `conversacion_history`; invocar send node → sin llamada Graph API ni `pending_manual`) → GREEN
- **Estimación**: ~95 líneas (+ ~90 test)

### T-S1-05: Registro del worker en Celery
- **Descripción**: En `agency/workers/celery_app.py`, agregar `workers.lead_persist_task` al `include` y route `workers.lead_persist_task.*` → cola `webhooks` (patrón DLQ).
- **REQs**: REQ-DM-LEAD-01 (procesamiento async)
- **Depende de**: T-S1-04
- **Archivos**: `agency/workers/celery_app.py`
- **Criterios**: `pytest tests/unit/test_celery_tasks.py` (task descubrible + routed a `webhooks`)
- **Estimación**: ~4 líneas

### T-S1-06: Resolución de tenant en webhook
- **Descripción**: En `agency/backend/webhooks/instagram_inbound.py`, `process_instagram_webhook_payload` resuelve `tenant_id = _resolve_tenant_from_payload(payload)` vía `tenants.instagram_business_account_id` (`media.owner.id`/`recipient.id`/`entry.id`) y publica SSE al tenant resuelto (no `"default"`). La extracción por keyword no cambia.
- **REQs**: REQ-DM-LEAD-01 (escenario tenant no-default)
- **Depende de**: T-S1-04
- **Archivos**: `agency/backend/webhooks/instagram_inbound.py`
- **Criterios**: `pytest tests/unit/test_lead_persist_task.py` (payload cuenta→`tenant_b` persiste con ese tenant)
- **Estimación**: ~25 líneas

### T-S1-07: Enqueue del worker desde main
- **Descripción**: En `agency/backend/main.py`, tras la extracción del webhook, encolar `persist_instagram_lead.delay(tenant_id, lead_data)` y responder 200 al webhook (desacoplado del trabajo).
- **REQs**: REQ-DM-LEAD-01
- **Depende de**: T-S1-06, T-S1-05
- **Archivos**: `agency/backend/main.py`
- **Criterios**: `pytest tests/unit/test_lead_persist_task.py` (flujo webhook → worker; 200 no bloqueado)
- **Estimación**: ~15 líneas

### T-S1-08: GET /{tenant}/leads expone scoring
- **Descripción**: En `agency/backend/routers/leads.py`, exponer `qualification_score`, `status` e `intent` en la respuesta del GET.
- **REQs**: REQ-DM-LEAD-01
- **Depende de**: T-S1-04
- **Archivos**: `agency/backend/routers/leads.py`
- **Criterios**: `pytest tests/unit/test_fastapi_endpoints.py` o `test_lead_automation.py` (GET devuelve los 3 campos)
- **Estimación**: ~15 líneas

## S2 — Voice Personas (PR #2, batch S2a: backend) — COMPLETADO (PR #24 + #25)

### T-S2a-01: Migración 012 — voice_personas + seed 3 personas ✅
- **Descripción**: Crear `agency/migrations/012_voice_personas.sql`: tabla `voice_personas` (id, name UNIQUE, description, edge_tts_voice, json2video_voice, locale_voices JSONB `'{}'`, is_active) + `scripts.voice_persona_id UUID REFERENCES voice_personas(id)` + seed idempotente de las 3 personas confirmadas (Masculina Enérgica: es-MX-JorgeNeural / Femenina Corporativa: es-MX-DaliaNeural / Fundador Tech: es-ES-AlvaroNeural, con `locale_voices` es/en).
- **REQs**: REQ-VOICE-01
- **Depende de**: —
- **Archivos**: `agency/migrations/012_voice_personas.sql`
- **Criterios**: `pytest tests/unit/test_voice_personas_api.py` (RED: seed → exactamente 3 activas con ambos voices → GREEN)
- **Estimación**: ~60 líneas

### T-S2a-02: Modelos VoicePersona + Script.voice_persona_id ✅
- **Descripción**: En `agency/backend/db/models.py`, agregar `VoicePersona` (edge_tts_voice, json2video_voice, locale_voices, is_active) y `Script.voice_persona_id`.
- **REQs**: REQ-VOICE-01, REQ-VOICE-04
- **Depende de**: T-S2a-01
- **Archivos**: `agency/backend/db/models.py`
- **Criterios**: `pytest tests/unit/test_voice_personas_api.py` (modelos mapean migración)
- **Estimación**: ~20 líneas

### T-S2a-03: Servicio voice_resolver ✅
- **Descripción**: Crear `agency/backend/services/voice_resolver.py` con `resolve_voice(persona: VoicePersona, lang: str) -> str`: `lang` derivado de `script.keyword` (`LANG:XX`, default `es`); devuelve `locale_voices[lang]` con fallback a `edge_tts_voice`.
- **REQs**: REQ-VOICE-02, REQ-VOICE-05
- **Depende de**: T-S2a-02
- **Archivos**: `agency/backend/services/voice_resolver.py`, `agency/tests/unit/test_voice_resolver.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_voice_resolver.py` (en→`en-US-ChristopherNeural`; lang desconocido → fallback `edge_tts_voice`) → GREEN
- **Estimación**: ~45 líneas (+ ~60 test)

### T-S2a-04: Router voice — listado y PATCH de persona ✅
- **Descripción**: Crear `agency/backend/routers/voice.py` (prefijo `/api/v1/tenants/{tenant_id}`): `GET /voice-personas` (solo `is_active=true`, ambos voices por motor) y `PATCH /scripts/{script_id}/voice-persona` body `{"voice_persona_id": uuid}` → persiste en `scripts.voice_persona_id`.
- **REQs**: REQ-VOICE-04
- **Depende de**: T-S2a-02
- **Archivos**: `agency/backend/routers/voice.py`, `agency/tests/unit/test_voice_personas_api.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_voice_personas_api.py` (GET lista 3; PATCH persiste persona P en script) → GREEN
- **Estimación**: ~70 líneas (+ ~55 test)

### T-S2a-05: Translate preserva persona ✅
- **Descripción**: En `agency/backend/routers/scripts.py`, `POST /scripts/{id}/translate` copia `voice_persona_id` al Script nuevo (`keyword=LANG:XX`) y lo expone en el dict del script.
- **REQs**: REQ-VOICE-05
- **Depende de**: T-S2a-04
- **Archivos**: `agency/backend/routers/scripts.py`
- **Criterios**: `pytest tests/unit/test_voice_personas_api.py` (script traducido conserva persona)
- **Estimación**: ~25 líneas

## S2 — Voice Personas (PR #2, batch S2b: frontend + render) — COMPLETADO (PR #3, size:exception)

### T-S2b-01: Render inyecta voz de persona por escena ✅
- **Descripción**: En `agency/workers/video_edit_task.py`, cargar `voice_persona_id` del script → `resolve_voice(persona, lang)` → inyectar `tts_voice` en cada `RenderScene` (Edge-TTS usa `scene.tts_voice or DEFAULT_VOICE`, ya soportado).
- **REQs**: REQ-VOICE-02, REQ-VOICE-05
- **Depende de**: T-S2a-03, T-S2a-05
- **Archivos**: `agency/workers/video_edit_task.py`
- **Criterios**: `pytest tests/unit/test_auto_publisher.py` (escenas llevan la voz de la persona, no `es-MX-JorgeNeural` por default; script `LANG:EN` → voz en inglés)
- **Estimación**: ~35 líneas

### T-S2b-02: json2video_client parametrizado ✅
- **Descripción**: En `agency/agents/mcp_servers/json2video_client.py`, `render_video(...)` recibe `voice` (default `es-MX-JorgeNeural`) y lo usa en el elemento `{type: "voice", model: "azure", voice: ...}` en lugar del hardcode.
- **REQs**: REQ-VOICE-03
- **Depende de**: T-S2a-01
- **Archivos**: `agency/agents/mcp_servers/json2video_client.py`, `agency/tests/unit/test_json2video.py` (extender)
- **Criterios**: RED `pytest tests/unit/test_json2video.py` (payload contiene `voice="X"` cuando persona es X) → GREEN
- **Estimación**: ~20 líneas (+ ~20 test)

### T-S2b-03: Selector de persona en Scriptwriting ✅
- **Descripción**: En `agency/frontend/src/features/Scriptwriting/views/ScriptInspectorView.jsx`, agregar selector "Voz de persona" (lista desde `GET /voice-personas`) que dispara `PATCH /scripts/{id}/voice-persona`; PublishApproval muestra la persona como badge aditivo (sin duplicar UI).
- **REQs**: REQ-VOICE-04
- **Depende de**: T-S2a-04
- **Archivos**: `agency/frontend/src/features/Scriptwriting/views/ScriptInspectorView.jsx`
- **Criterios**: `pytest tests/unit/test_frontend_features_phase11.py` o `test_frontend_structure.py` (selector presente + PATCH en el inspector)
- **Estimación**: ~80 líneas

## S3 — Auto-Publicación (PR #3)

> **Estado**: ✅ Mergeado a `main` vía PR #29 (2026-08-19) con size:exception aprobada (~916 líneas de código por forecast subestimado + artefactos openspec del change). Rebase sobre main previo limpio tras resolver conflictos S1↔S3 (test_db_indexes, celery_app, test_celery_tasks). Gate: 398 passed, 3 skipped, 1 deselected + ruff limpio. Fix incluido: test_publisher_task filtra por tenant (acoplamiento de orden con test_calendar_api).

### T-S3-01: Migración 013 — videos.platform + tenants.best_time_slot
- **Descripción**: Crear `agency/migrations/013_videos_platform.sql`: `videos.platform TEXT NOT NULL DEFAULT 'instagram'` y `tenants.best_time_slot JSONB`.
- **REQs**: REQ-PUB-01, REQ-PUB-05 (persistencia del slot)
- **Depende de**: —
- **Archivos**: `agency/migrations/013_videos_platform.sql`
- **Criterios**: `pytest tests/unit/test_db_indexes.py` (extendido: migración 013 existe + `platform` default `'instagram'`)
- **Estimación**: ~20 líneas

### T-S3-02: Modelos Video.platform + Tenant.best_time_slot
- **Descripción**: En `agency/backend/db/models.py`, agregar `Video.platform` (default `'instagram'`) y `Tenant.best_time_slot` (JSONB, nullable).
- **REQs**: REQ-PUB-01, REQ-PUB-05
- **Depende de**: T-S3-01
- **Archivos**: `agency/backend/db/models.py`
- **Criterios**: `pytest tests/unit/test_db_indexes.py` (modelos declaran columnas)
- **Estimación**: ~10 líneas

### T-S3-03: publisher_task delega al microservicio
- **Descripción**: En `agency/workers/publisher_task.py`, reemplazar el cuerpo de `auto_publish_scheduled_videos_task`: 1) SELECT videos `publish_approval_status='approved'` y `published_at <= now_utc`; 2) por video, `_build_credentials(tenant)` tenant-first (`instagram_graph_api_token_ref`/`instagram_business_account_id`, fallback env dev) y ruta por `video.platform` vía factory de `microservices/publisher/adapters.py`; 3) `POST {PUBLISHER_URL}/publish` (mismo contrato que `agents/nodes/publish.py`) con idempotency_key; 4) write-back `post_id` + `published_at` + `status='published'`. No re-publica videos ya `published`.
- **REQs**: REQ-PUB-02, REQ-PUB-04, REQ-PUB-07
- **Depende de**: T-S3-02
- **Archivos**: `agency/workers/publisher_task.py`, `agency/tests/unit/test_publisher_task.py` (crear/modificar, nuevo contrato)
- **Criterios**: RED `pytest tests/unit/test_publisher_task.py` (factory rutea `platform='tiktok'` → TikTokPublisher; video `approved` sin `published_at` → publica y persiste post_id; re-ejecución no llama al publisher; tenant con token → token del tenant, sin token → env) → GREEN
- **Estimación**: ~100 líneas (+ ~60 test)

### T-S3-04: Celery include + beat_schedule diario
- **Descripción**: En `agency/workers/celery_app.py`, agregar `workers.publisher_task` al `include`, `beat_schedule = {"auto-publish-daily": {task: "workers.publisher_task.auto_publish_scheduled_videos_task", schedule: crontab(hour=os.getenv("AUTO_PUBLISH_HOUR", "8"), minute=0)}}` y route a cola `default`.
- **REQs**: REQ-PUB-03, REQ-PUB-06 (beat armado)
- **Depende de**: T-S3-03
- **Archivos**: `agency/workers/celery_app.py`
- **Criterios**: `pytest tests/unit/test_celery_tasks.py` (task en include + entry diario en beat_schedule)
- **Estimación**: ~20 líneas

### T-S3-05: Servicio best_time con Gemini + fallback
- **Descripción**: Crear `agency/backend/services/best_time.py` con `suggest_best_time(tenant_id) -> {"day_of_week", "hour", "source"}`: prompt acotado con agregados de `video_metrics` vía `agents.llm.acomplete` (Gemini) → JSON {day, hour}; si falla/timeout → heurística de pico histórico (`max views_72h` por dow/hour); se persiste en `tenants.best_time_slot` con `source`.
- **REQs**: REQ-PUB-05
- **Depende de**: T-S3-02
- **Archivos**: `agency/backend/services/best_time.py`, `agency/tests/unit/test_best_time.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_best_time.py` (Gemini responde → slot persistido con `source=gemini`; Gemini falla → slot heurístico persistido) → GREEN
- **Estimación**: ~85 líneas (+ ~70 test)

### T-S3-06: Calendar persiste platform
- **Descripción**: En `agency/backend/routers/calendar.py`, `POST /calendar/schedule` persiste `video.platform = req.platform` (hoy lo descarta) además de crear registro, `status='approved'` y `published_at=scheduled_at`.
- **REQs**: REQ-PUB-06
- **Depende de**: T-S3-03, T-S3-04
- **Archivos**: `agency/backend/routers/calendar.py`, `agency/tests/unit/test_calendar_api.py` (extender)
- **Criterios**: `pytest tests/unit/test_calendar_api.py` (POST crea registro + persiste platform + arma beat)
- **Estimación**: ~10 líneas

## S4 — Competitor Benchmark (PR #4)

### T-S4-01: Migración 014 — competitor_accounts
- **Descripción**: Crear `agency/migrations/014_competitor_accounts.sql`: tabla `competitor_accounts` (id, tenant_id FK CASCADE, platform, username, display_name, niche, is_active, created_at) + `idx_competitor_accounts_tenant (tenant_id, is_active)`.
- **REQs**: REQ-COMP-01
- **Depende de**: —
- **Archivos**: `agency/migrations/014_competitor_accounts.sql`
- **Criterios**: `pytest tests/unit/test_db_indexes.py` (extendido: migración 014 existe) + `test_competitor_ingest.py`
- **Estimación**: ~25 líneas

### T-S4-02: Modelo CompetitorAccount
- **Descripción**: En `agency/backend/db/models.py`, agregar `CompetitorAccount` con los campos de 014.
- **REQs**: REQ-COMP-01
- **Depende de**: T-S4-01
- **Archivos**: `agency/backend/db/models.py`
- **Criterios**: `pytest tests/unit/test_competitor_ingest.py` (modelo crea fila con tenant/platform/niche)
- **Estimación**: ~15 líneas

### T-S4-03: rag_context con fuente (source)
- **Descripción**: En `agency/backend/services/rag_context.py`, extender `index_winning_pattern(tenant_id, pattern_text, viral_score, niche="", source="own", account_id=None)` (payload `+{"source", "account_id"}`; `"own"` = compat con `analytics_agent`, mismo hash 384-d de `simple_embedding`) y `get_winning_patterns(niche="", query="", limit=3, source=None)` con filtro opcional.
- **REQs**: REQ-COMP-03, REQ-COMP-04
- **Depende de**: T-S4-02
- **Archivos**: `agency/backend/services/rag_context.py`
- **Criterios**: `pytest tests/unit/test_ingest_knowledge.py` o `test_competitor_ingest.py` (payload con `source="competitor"`; filtro por source; default `"own"` no rompe analytics_agent)
- **Estimación**: ~25 líneas

### T-S4-04: Servicio competitor_ingest
- **Descripción**: Crear `agency/backend/services/competitor_ingest.py` con `ingest_competitor(account) -> int`: `asearxng_search_sanitized(f"{username} {niche} gancho viral", num_results=5)` (cache 6h existente) → `extract_hook_structure(title, snippet)` → `index_winning_pattern(..., source="competitor", account_id=...)` en Qdrant. Solo cuentas `is_active`.
- **REQs**: REQ-COMP-02, REQ-COMP-03
- **Depende de**: T-S4-03
- **Archivos**: `agency/backend/services/competitor_ingest.py`, `agency/tests/unit/test_competitor_ingest.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_competitor_ingest.py` (hook indexado con `source="competitor"` y hash 384-d) → GREEN
- **Estimación**: ~85 líneas (+ ~60 test)

### T-S4-05: Router competitors CRUD + trigger ingestión
- **Descripción**: Crear `agency/backend/routers/competitors.py` (prefijo `/api/v1/tenants/{tenant_id}`): `GET /competitors`, `POST /competitors` `{platform, username, display_name, niche}`, `PATCH /competitors/{id}` (toggle `is_active`) y `POST /competitors/{id}/ingest` → dispara `ingest_competitor`.
- **REQs**: REQ-COMP-01, REQ-COMP-02
- **Depende de**: T-S4-04
- **Archivos**: `agency/backend/routers/competitors.py`
- **Criterios**: `pytest tests/unit/test_competitor_benchmark_api.py` (creación persiste; ingest manual dispara indexación)
- **Estimación**: ~70 líneas

### T-S4-06: Endpoint GET /{tenant}/rag/benchmark
- **Descripción**: En `agency/backend/routers/rag.py`, agregar `GET /{tenant}/rag/benchmark?niche=X&limit=5` → `{"own_hooks", "competitor_hooks", "top_similar", "gaps"}`: propios (`source="own"` o ausente) vs ajenos (`source="competitor"` y solo cuentas activas), top-N por similitud + gap analysis determinista por estructura.
- **REQs**: REQ-COMP-04
- **Depende de**: T-S4-03, T-S4-04
- **Archivos**: `agency/backend/routers/rag.py`, `agency/tests/unit/test_competitor_benchmark_api.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_competitor_benchmark_api.py` (devuelve top-N + gaps; cuenta inactiva excluida) → GREEN
- **Estimación**: ~55 líneas (+ ~55 test)

## S5 — PDF Reports (PR #5)

### T-S5-01: Migración 015 — tenants.cost_per_video_usd
- **Descripción**: Crear `agency/migrations/015_tenant_cost_per_video.sql`: `ALTER TABLE tenants ADD COLUMN IF NOT EXISTS cost_per_video_usd NUMERIC(10,2) NOT NULL DEFAULT 5.00` (decisión usuario P5: default 5 USD).
- **REQs**: REQ-PDF-03
- **Depende de**: —
- **Archivos**: `agency/migrations/015_tenant_cost_per_video.sql`
- **Criterios**: `pytest tests/unit/test_db_indexes.py` (extendido: migración 015 existe) + `test_pdf_generator.py` (default 5.00)
- **Estimación**: ~10 líneas

### T-S5-02: Modelo Tenant.cost_per_video_usd
- **Descripción**: En `agency/backend/db/models.py`, agregar `Tenant.cost_per_video_usd` (NUMERIC, default 5.00).
- **REQs**: REQ-PDF-03
- **Depende de**: T-S5-01
- **Archivos**: `agency/backend/db/models.py`
- **Criterios**: `pytest tests/unit/test_pdf_generator.py` (default 5 USD)
- **Estimación**: ~4 líneas

### T-S5-03: Dependencias weasyprint + reportlab
- **Descripción**: En `requirements.txt` (raíz), agregar `weasyprint` y `reportlab` (fallback si `libpango` no está en el contenedor).
- **REQs**: REQ-PDF-01
- **Depende de**: —
- **Archivos**: `requirements.txt`
- **Criterios**: `pytest tests/unit/test_pdf_generator.py` (imports resuelven o fallback reportlab)
- **Estimación**: ~2 líneas

### T-S5-04: Helpers SVG de gráficos
- **Descripción**: Crear `agency/backend/reports/chart_svg.py` con `bar_chart(distribution)` y `line_chart(views_por_video_top_n)` devolviendo strings SVG embebibles.
- **REQs**: REQ-PDF-01 (gráficos SVG)
- **Depende de**: —
- **Archivos**: `agency/backend/reports/chart_svg.py`
- **Criterios**: `pytest tests/unit/test_pdf_generator.py` (SVG string con barras/líneas válidas)
- **Estimación**: ~50 líneas

### T-S5-05: pdf_generator → bytes PDF reales
- **Descripción**: En `agency/backend/reports/pdf_generator.py`, reescribir `generate_tenant_pdf_report(tenant_id, metrics_summary, leads_count, qualified_leads, videos_count, cost_per_video_usd) -> bytes`: KPIs reales de `video_metrics`/`leads`/`videos` (no hardcodeados), charts SVG, ROI (`investment = cost_per_video_usd * videos_count`, `est_return = qualified_leads * ASSUMED_LEAD_VALUE` default 50 USD, `roi_pct`); `weasyprint.HTML(string=html).write_pdf()` con except → reportlab platypus. Sin leads → sección vacía sin error.
- **REQs**: REQ-PDF-01, REQ-PDF-03
- **Depende de**: T-S5-02, T-S5-04
- **Archivos**: `agency/backend/reports/pdf_generator.py`, `agency/tests/unit/test_pdf_generator.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_pdf_generator.py` (PDF embebe KPIs reales, no 0.84/48; sin leads → sección vacía sin error; costo custom C con N videos → investment C×N) → GREEN
- **Estimación**: ~135 líneas (+ ~75 test)

### T-S5-06: Endpoint monthly-pdf binario
- **Descripción**: En `agency/backend/routers/metrics.py`, `GET /{tenant}/reports/monthly-pdf` → `Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="viralsync_report_{tenant}.pdf"'})`; body empieza con `%PDF`. El comportamiento metadata-JSON queda reemplazado (ruta auxiliar `/reports/monthly-pdf/meta` como fallback hasta verify).
- **REQs**: REQ-PDF-02
- **Depende de**: T-S5-05
- **Archivos**: `agency/backend/routers/metrics.py`, `agency/tests/unit/test_monthly_pdf_endpoint.py` (crear)
- **Criterios**: RED `pytest tests/unit/test_monthly_pdf_endpoint.py` (body inicia `%PDF` + content-type `application/pdf`) → GREEN
- **Estimación**: ~25 líneas (+ ~55 test)

### T-S5-07: Botón descarga en /analytics
- **Descripción**: En `agency/frontend/src/app/analytics/page.js`, botón "Descargar PDF" → `fetch(.../reports/monthly-pdf)` → blob → `URL.createObjectURL` → `<a download>`; KPIs de tarjetas pasan a consumir `/metrics` reales.
- **REQs**: REQ-PDF-04
- **Depende de**: T-S5-06
- **Archivos**: `agency/frontend/src/app/analytics/page.js`
- **Criterios**: `pytest tests/unit/test_frontend_features_phase11.py` (botón presente + descarga `application/pdf`)
- **Estimación**: ~35 líneas

## Review Workload Forecast

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium
```

| Slice | PR | Líneas est. | Riesgo >400 | Decisión |
|-------|----|-------------|-------------|----------|
| S1 DM Leads CRM | PR #1 (base main) | ≈360–410 (344 tabla diseño + 2 tests extra) | Medio (roza; contingencia S1a/S1b) | Confirmado — force-chained, no preguntar |
| S2 Voice Personas | PR #2 (base main tras #1); 2 batches apply: S2a backend ≈335 / S2b frontend+render ≈180 | ≈515 total, ≤335 por batch | Bajo por batch (único slice >400 → partido S2a/S2b) | Confirmado — force-chained, no preguntar |
| S3 Auto-Publicación | PR #3 (base main tras #2) | ≈375 | Medio | Confirmado — force-chained, no preguntar |
| S4 Competitor Benchmark | PR #4 (base main tras #3) | ≈390 | Medio (roza; contingencia S4a/S4b) | Confirmado — force-chained, no preguntar |
| S5 PDF Reports | PR #5 (base main tras #4) | ≈391 | Medio (roza; contingencia S5a/S5b) | Confirmado — force-chained, no preguntar |

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| S1 | Persistir+scorear+wiring leads (gateado envío) | PR #1 | `cd agency && ../venv/bin/python -m pytest tests/unit/test_lead_scoring.py tests/unit/test_lead_persist_task.py tests/unit/test_db_indexes.py` | Webhook POST `/webhooks/instagram` con payload HMAC real → worker → `GET /{tenant}/leads` | Revert PR #1: drop columnas 011 + desregistrar worker; `node_send_dm_reply` intacto |
| S2 | Catálogo+selector+render por persona (2 batches) | PR #2 | `pytest tests/unit/test_voice_resolver.py tests/unit/test_voice_personas_api.py tests/unit/test_json2video.py` | Render de script con persona vía pipeline video_edit; select persona en Scriptwriting | Revert PR #2: drop tabla 012 + columna scripts; render vuelve a default |
| S3 | Auto-publish + best-time Gemini | PR #3 | `pytest tests/unit/test_publisher_task.py tests/unit/test_best_time.py tests/unit/test_celery_tasks.py` | `celery -A workers.celery_app beat` + ejecución manual del task con video `approved` vencido (mock :8002) | Revert PR #3: drop 013 + desregistrar beat_schedule; grafo/publish intactos |
| S4 | Benchmark propios vs competidores | PR #4 | `pytest tests/unit/test_competitor_ingest.py tests/unit/test_competitor_benchmark_api.py` | POST `/competitors` → POST `/competitors/{id}/ingest` → `GET /{tenant}/rag/benchmark` | Revert PR #4: drop 014 + endpoint nuevo removido (rutas rag existentes intactas) |
| S5 | PDF binario + ROI configurable | PR #5 | `pytest tests/unit/test_pdf_generator.py tests/unit/test_monthly_pdf_endpoint.py` | `GET /{tenant}/reports/monthly-pdf` → body `%PDF` + descarga en `/analytics` | Revert PR #5: drop 015 + endpoint binario; ruta `/monthly-pdf/meta` fallback hasta verify |
