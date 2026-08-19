# Design: 5-value-leaps

ViralSync — 5 Value Leaps (S1 DM Leads CRM, S2 Voice Personas, S3 Auto-Publish, S4 Competitor Benchmark, S5 PDF Reports). Diseño por slice, encadenados en orden S1→S5. Regla: si un slice supera ~400 líneas, se divide en sub-slices (indicado por slice).

Nota de numeración de migraciones: `proposal.md` decía "011 para `videos.platform`", pero como S1 y S2 se implementan antes, la numeración sigue el orden de implementación: **011 (S1), 012 (S2), 013 (S3 videos.platform), 014 (S4), 015 (S5)**. Todas idempotentes (patrón `ADD COLUMN IF NOT EXISTS` de 002).

---

## S1 — DM Leads CRM (P3)

### Arquitectura (patrón)

Worker Celery async por webhook (mismo patrón que `workers/webhook_dlq_task.py`): el endpoint `POST /webhooks/instagram` resuelve tenant y encola `persist_instagram_lead` en la cola `webhooks`; el worker persiste con **idempotencia por hash**, scorea, y corre la clasificación `dm_graph` (best-effort). Servicio puro de scoring (patrón `trend_scorer.py`: reglas + umbrales, testable sin DB). Envío **GATEADO**: `node_send_dm_reply` no se toca.

### Archivos a tocar (ruta real | acción | est. líneas)

| Ruta | Acción | Est. líneas |
|---|---|---|
| `agency/migrations/011_leads_qualification.sql` | Crear | ~35 |
| `agency/backend/db/models.py` | Modificar (`Lead`: +`qualification_score`, +`platform`, +`dedup_hash`) | ~10 |
| `agency/backend/services/lead_scoring.py` | Crear | ~55 |
| `agency/workers/lead_persist_task.py` | Crear | ~95 |
| `agency/workers/celery_app.py` | Modificar (include + route `webhooks`) | ~4 |
| `agency/backend/webhooks/instagram_inbound.py` | Modificar (resolver account→tenant, sin persistir) | ~25 |
| `agency/backend/main.py` | Modificar (enqueue worker tras extracción) | ~15 |
| `agency/backend/routers/leads.py` | Modificar (exponer `qualification_score`, `status`, `intent` en GET) | ~15 |
| `agency/tests/unit/test_lead_persist_task.py` | Crear | ~90 |
| **Total** | | **~344** |

### Contratos (endpoints/columnas/firmas)

- **Migración `011_leads_qualification.sql`**:
  ```sql
  ALTER TABLE leads
      ADD COLUMN IF NOT EXISTS qualification_score INTEGER NOT NULL DEFAULT 0,
      ADD COLUMN IF NOT EXISTS platform TEXT NOT NULL DEFAULT 'instagram',
      ADD COLUMN IF NOT EXISTS dedup_hash TEXT,
      ALTER COLUMN video_id DROP NOT NULL;   -- el webhook no siempre tiene video
  CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_dedup_hash ON leads (dedup_hash);
  CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);
  ```
  *(hallazgo: `leads.video_id` es `NOT NULL REFERENCES videos(id)` — el webhook no trae video; sin `DROP NOT NULL` el INSERT de webhook fallaría)*
- **Servicio** `lead_scoring.py`:
  ```python
  def score_lead(message: str, intent: str) -> tuple[int, str]
  # -> (score 0-100, status) | status: "Nuevo" | "Contactado" | "Calificado"
  # purchase_intent + keyword precio/demo -> >=60 Calificado
  # spam o sin keywords -> <30 Nuevo
  ```
- **Worker** `lead_persist_task.py`:
  ```python
  @celery_app.task(name="workers.lead_persist_task.persist_instagram_lead")
  def persist_instagram_lead(tenant_id: str, lead_data: dict) -> dict
  # lead_data: {ig_user_id, mensaje_original, origen, keyword}
  # 1. dedup: sha256(ig_user_id + "|" + mensaje_original) -> si existe, retorna el existente
  # 2. INSERT Lead(tenant_id, platform='instagram', status='Nuevo', ...)
  # 3. score + status via score_lead
  # 4. best-effort: intent = classify_intent() -> persistir JSON {intent, ts} en conversacion_history
  ```
- **Webhook**: `process_instagram_webhook_payload(payload)` → además resuelve `tenant_id = _resolve_tenant_from_payload(payload)` usando `tenants.instagram_business_account_id` (`media.owner.id`/`recipient.id`/`entry.id`); SSE pasa a publicar al tenant resuelto (no `"default"`).

### Flujo (paso a paso numerado)

1. Meta POST `/webhooks/instagram` → validación HMAC existente (sin cambios).
2. `process_instagram_webhook_payload` extrae leads por keyword (sin cambios en extracción) y **resuelve tenant** por `instagram_business_account_id`.
3. `main.py` encola `persist_instagram_lead.delay(tenant_id, lead_data)` (patrón DLQ) y responde 200 al webhook.
4. Worker: dedup por `dedup_hash` → INSERT `Lead` (status `Nuevo`, `platform=instagram`) → `score_lead` → update `qualification_score` + `status`.
5. Clasificación `dm_graph`: se invoca `build_dm_graph()` con state mínimo (`tenant_id`, `lead_id`, `incoming_message`); se persiste `intent`/`confidence` como JSON en `conversacion_history`. Si Qdrant/LLM fallan → fallback `classify_intent` (reglas) y se continúa (nunca rompe la persistencia).
6. `node_send_dm_reply` NO cambia (gateado): solo log + SSE, sin llamada a Graph API ni `pending_manual`.
7. `GET /{tenant}/leads` expone `qualification_score`, `status`, `intent`.

### Decisiones técnicas (cada una con justificación 1-2 líneas)

| Decisión | Justificación |
|---|---|
| Worker Celery (cola `webhooks`) en vez de persistir inline | Patrón existente del repo (`webhook_dlq_task`); desacopla el 200 del webhook del trabajo de DB/LLM y permite retry. |
| Idempotencia por `dedup_hash` UNIQUE (sha256 user+message) | REQ-DM-LEAD-05; evita duplicados ante redelivery de Meta sin tabla extra. |
| `video_id` pasa a nullable en 011 | Hallazgo: webhook no tiene video_id; sin esto el INSERT falla por FK NOT NULL. |
| Scoring como servicio puro sin IO | Testeable unit sin DB (patrón `trend_scorer.py`); reglas + umbrales deterministas. |
| `dm_graph` best-effort con fallback a `classify_intent` | Wiring real (REQ-DM-LEAD-04) sin acoplar la persistencia a Qdrant/LLM (que pueden fallar offline). |
| Envío gateado: `node_send_dm_reply` intacto | Decisión de usuario (P3): sin app Meta prod, S1 no simula envío (REQ-DM-LEAD-06). |
| SSE al tenant resuelto | Mitiga el riesgo "webhook sin scoping tenant" de la proposal. |

### Tests propuestos (ruta)

- `agency/tests/unit/test_lead_scoring.py` — REQ-DM-LEAD-03 (high-intent ≥60/Calificado; spam <30/Nuevo).
- `agency/tests/unit/test_lead_persist_task.py` — REQ-DM-LEAD-01/02/04/05/06: persistencia con tenant resuelto, dedup sin duplicado, clasificación en `conversacion_history`, sin side-effects de envío.
- `agency/tests/unit/test_db_indexes.py` (extender) — REQ-DM-LEAD-02: índice `status` + columna `qualification_score` tras migración.

### Estimación total + riesgo budget

~344 líneas. Riesgo budget: **Bajo-Medio** (cabe en 400). Si `dm_graph` wiring creciera (LLM mock complejo), partir: S1a persist+score / S1b wiring dm_graph.

---

## S2 — Voice Personas (P2)

### Arquitectura (patrón)

Catálogo DB + **resolución de voz por (persona, idioma)** en un servicio (`voice_resolver`): el script persiste `voice_persona_id`; el render (Edge-TTS por escena y json2video Azure) recibe la voz resuelta. Reuso del pipeline existente: el renderer ya soporta `tts_voice` por escena (`RenderScene.tts_voice`, `voice = scene.tts_voice or DEFAULT_VOICE`) y `video_edit_task._storyboard_to_scenes` ya lo propaga — solo falta llenarlo desde la persona.

### Archivos a tocar (ruta real | acción | est. líneas)

| Ruta | Acción | Est. líneas |
|---|---|---|
| `agency/migrations/012_voice_personas.sql` | Crear (tabla + columna scripts + seed 3 personas) | ~60 |
| `agency/backend/db/models.py` | Modificar (`VoicePersona`, `Script.voice_persona_id`) | ~20 |
| `agency/backend/services/voice_resolver.py` | Crear (voz por persona+idioma; mapeo LANG→voice) | ~45 |
| `agency/backend/routers/voice.py` | Crear (GET personas, PATCH script persona) | ~70 |
| `agency/backend/routers/scripts.py` | Modificar (translate copia `voice_persona_id`; expone en dict) | ~25 |
| `agency/workers/video_edit_task.py` | Modificar (scenes `tts_voice` desde persona resuelta) | ~35 |
| `agency/agents/mcp_servers/json2video_client.py` | Modificar (parametrizar `voice`) | ~20 |
| `agency/frontend/src/features/Scriptwriting/views/ScriptInspectorView.jsx` | Modificar (selector de persona) | ~80 |
| `agency/tests/unit/test_voice_resolver.py` | Crear | ~60 |
| `agency/tests/unit/test_voice_personas_api.py` | Crear | ~55 |
| **Total** | | **~470** |

### Contratos (endpoints/columnas/firmas)

- **Migración `012_voice_personas.sql`**:
  ```sql
  CREATE TABLE IF NOT EXISTS voice_personas (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name TEXT NOT NULL UNIQUE,
      description TEXT,
      edge_tts_voice TEXT NOT NULL,
      json2video_voice TEXT NOT NULL,
      locale_voices JSONB NOT NULL DEFAULT '{}',  -- {"es": "es-MX-JorgeNeural", "en": "en-US-ChristopherNeural", ...}
      is_active BOOLEAN NOT NULL DEFAULT TRUE
  );
  ALTER TABLE scripts ADD COLUMN IF NOT EXISTS voice_persona_id UUID REFERENCES voice_personas(id);
  -- Seed (3 personas confirmadas por el usuario):
  --  Masculina Enérgica  | edge: es-MX-JorgeNeural  | azure: es-MX-JorgeNeural  | en: en-US-ChristopherNeural
  --  Femenina Corporativa| edge: es-MX-DaliaNeural  | azure: es-MX-DaliaNeural  | en: en-US-JennyNeural
  --  Fundador Tech       | edge: es-ES-AlvaroNeural | azure: es-ES-AlvaroNeural | en: en-US-GuyNeural
  ```
- **Servicio**:
  ```python
  def resolve_voice(persona: VoicePersona, lang: str) -> str
  # lang se deriva de script.keyword ("LANG:XX"); default "es"
  # devuelve edge_tts_voice (locale_voices[lang] o fallback)
  ```
- **API** (`routers/voice.py`, prefijo `/api/v1/tenants/{tenant_id}`):
  - `GET /voice-personas` → lista activa (`is_active=true`) con ambos voice por motor.
  - `PATCH /scripts/{script_id}/voice-persona` body `{"voice_persona_id": uuid}` → persiste en `scripts.voice_persona_id`.
- **json2video_client**: `render_video(script, keywords, tenant_id, title, voice="es-MX-JorgeNeural")` → usa `voice` en el elemento `{type: "voice", model: "azure", voice: ...}` (hoy hardcodeado).

### Flujo (paso a paso numerado)

1. Migración crea tabla + seed 3 personas y columna en scripts.
2. Frontend Scriptwriting: selector "Voz de persona" en el inspector → `PATCH /scripts/{id}/voice-persona`.
3. Traducción (`POST /scripts/{id}/translate`): el Script nuevo (`keyword=LANG:XX`) **copia** `voice_persona_id` del original (REQ-VOICE-05).
4. Render: `video_edit_task` carga persona → `resolve_voice(persona, lang)` → inyecta `tts_voice` en cada escena (Edge-TTS) y pasa `voice` a `json2video_client.render_video` (Azure).
5. Renderer Edge-TTS usa `scene.tts_voice` (ya soportado) → audio con la voz de la persona, no el default.
6. PublishApproval: el badge de variante muestra la persona (si aplica; aditivo).

### Decisiones técnicas (cada una con justificación 1-2 líneas)

| Decisión | Justificación |
|---|---|
| Voz por idioma en `locale_voices` (JSONB) dentro de la misma tabla | REQ-VOICE-05 exige voz del idioma destino sin tabla extra; JSONB permite crecer idiomas sin migración. |
| `voice_persona_id` en `scripts` (no en scenes) | La persona es propiedad del script; las scenes se derivan en render (menos columnas que tocar). |
| Selector solo en Scriptwriting + PATCH | REQ-VOICE-04; PublishApproval lee la persona desde el script (aditivo, sin duplicar UI). |
| No ElevenLabs | Decisión de usuario (P2): Edge-TTS + Azure de json2video únicamente. |
| Resolver idioma desde `keyword=LANG:XX` | Convención ya existente del flujo translate (no inventar campo nuevo). |

### Estimación total + riesgo budget

~470 líneas. Riesgo budget: **Medio-Alto — EXCEDE 400** → **partir en sub-slices**: S2a backend+migración (tabla 60 + modelo 20 + resolver 45 + router 70 + scripts 25 + tests 115 ≈ **335**) / S2b frontend+render flow (video_edit 35 + json2video 20 + selector 80 + tests ≈ **180**). S2a primero (desbloquea API), S2b encadenado.

---

## S3 — Auto-Publicación (P1)

### Arquitectura (patrón)

**PublisherFactory ya existe** en `microservices/publisher/adapters.py` (Instagram/TikTok/YT + `publish_reel_once` idempotente) y el grafo ya publica vía `POST {PUBLISHER_URL}/publish`. El problema es que `publisher_task.py` duplica el flujo con tokens env. Se **reemplaza el cuerpo del task** para delegar al microservicio (mismo contrato que `agents/nodes/publish.py`), con credenciales tenant-first. Best-time: servicio LLM (Gemini vía `agents.llm.acomplete`, cuyo DIRECT_CHAIN ya prioriza Gemini) con fallback heurístico sobre `video_metrics`. Beat schedule diario escanea videos `approved` vencidos.

### Archivos a tocar (ruta real | acción | est. líneas)

| Ruta | Acción | Est. líneas |
|---|---|---|
| `agency/migrations/013_videos_platform.sql` | Crear (`videos.platform`, `tenants.best_time_slot`) | ~20 |
| `agency/backend/db/models.py` | Modificar (`Video.platform`, `Tenant.best_time_slot`) | ~10 |
| `agency/workers/publisher_task.py` | Modificar (delegar a `:8002`, credenciales tenant-first, respetar `platform`) | ~100 |
| `agency/backend/services/best_time.py` | Crear (Gemini + fallback heurístico) | ~85 |
| `agency/workers/celery_app.py` | Modificar (include `publisher_task` + `beat_schedule` diario + route) | ~20 |
| `agency/backend/routers/calendar.py` | Modificar (persistir `req.platform` en `videos.platform`) | ~10 |
| `agency/tests/unit/test_best_time.py` | Crear | ~70 |
| `agency/tests/unit/test_publisher_task.py` | Modificar (nuevo contrato) | ~60 |
| **Total** | | **~375** |

### Contratos (endpoints/columnas/firmas)

- **Migración `013_videos_platform.sql`**:
  ```sql
  ALTER TABLE videos ADD COLUMN IF NOT EXISTS platform TEXT NOT NULL DEFAULT 'instagram';
  ALTER TABLE tenants ADD COLUMN IF NOT EXISTS best_time_slot JSONB;  -- {"day_of_week": 2, "hour": 19, "source": "gemini"|"heuristic"}
  ```
- **Task** `auto_publish_scheduled_videos_task` (firma sin cambios) → nuevo cuerpo:
  ```python
  # 1. SELECT videos WHERE publish_approval_status='approved' AND published_at <= now_utc
  # 2. por video: credenciales = _build_credentials(tenant)  # instagram_graph_api_token_ref/instagram_business_account_id del tenant; fallback env (dev)
  # 3. POST {PUBLISHER_URL}/publish {platform: video.platform, video_url: edited_video_uri, ...idempotency_key}
  # 4. write-back: instagram_post_id (o post_id por plataforma) + published_at + status='published'
  # Idempotencia: solo videos 'approved'; re-ejecución no matchea videos ya 'published'
  ```
- **Servicio** `best_time.py`:
  ```python
  async def suggest_best_time(tenant_id: str) -> dict  # {"day_of_week", "hour", "source"}
  # Gemini: prompt acotado con agregados de video_metrics (views por hora/día) -> JSON {day, hour}
  # fallback: hora/día de pico histórico (max views_72h por dow/hour en video_metrics)
  ```
- **Celery** (`celery_app.conf`):
  ```python
  include += ["workers.publisher_task"]
  beat_schedule = {"auto-publish-daily": {"task": "workers.publisher_task.auto_publish_scheduled_videos_task",
                   "schedule": crontab(hour=os.getenv("AUTO_PUBLISH_HOUR", "8"), minute=0)}}
  task_routes["workers.publisher_task.*"] = {"queue": "default"}
  ```
- **Calendar**: `POST /calendar/schedule` persiste `video.platform = req.platform` (hoy lo descarta).

### Flujo (paso a paso numerado)

1. Migración agrega `videos.platform` (default `instagram`) + `tenants.best_time_slot`.
2. `POST /calendar/schedule`: crea el registro, `status='approved'`, `published_at=scheduled_at`, y ahora **persiste `platform`** en el video (REQ-PUB-06; el beat diario ya armado lo recoge).
3. Beat diario ejecuta `auto_publish_scheduled_videos_task`: escanea videos `approved` vencidos.
4. Por video: `_build_credentials` (tenant-first, fallback env) → `POST :8002/publish` con `platform` real → write-back post_id + `published_at` + `status='published'`.
5. Re-ejecución: videos ya `published` no matchean la query (idempotente, REQ-PUB-04); además `publish_reel_once` dedupe por key (RESILIENCE-001).
6. Best-time: `suggest_best_time(tenant)` (Gemini; fallback heurístico) → se persiste en `tenants.best_time_slot` y se expone en el modal de calendario (sugerencia).
7. El write-path del grafo (`agents/nodes/publish.py`) NO se modifica (non-goal).

### Decisiones técnicas (cada una con justificación 1-2 líneas)

| Decisión | Justificación |
|---|---|
| Delegar `publisher_task` al micro `:8002` en vez de duplicar Meta calls | Elimina la duplicación env-vs-per-tenant (riesgo de la proposal); reusa adapters + idempotencia existentes. |
| Credenciales tenant-first con fallback env | REQ-PUB-07; sin romper el path dev (tokens `token_` simulan en el adaptador). |
| Idempotencia por filtro `approved` + `publish_reel_once` | REQ-PUB-04: status cambia a `published` → la re-ejecución no re-publica; key SHA-256 cubre redelivery. |
| Best-time con Gemini (prompt acotado) + fallback heurístico | Decisión de usuario (P1); el DIRECT_CHAIN de `agents.llm` ya prioriza Gemini. |
| `best_time_slot` JSONB en tenants | REQ-PUB-05 exige persistencia del slot; JSONB flexible para el shape del LLM. |
| No tocar `agents/nodes/publish.py` | Non-goal explícito: el grafo sigue siendo el único write-path interactivo. |

### Estimación total + riesgo budget

~375 líneas. Riesgo budget: **Medio** (cabe en 400). Si el mock de Gemini creciera, partir S3a migración+task+celery / S3b best-time.

---

## S4 — Competitor Benchmark (P4)

### Arquitectura (patrón)

Catálogo DB `competitor_accounts` + **ingestión manual y SearXNG reusando el patrón existente** (`asearxng_search_sanitized` ya cachea 6h en Redis). El extractor de estructura de ganchos indexa en Qdrant `marketing_brain` con el **mismo hash 384-d** de `rag_context.simple_embedding` y `source="competitor"` en payload. Benchmark: consulta filtrada por `source` + gap analysis (estructuras propias vs ajenas).

### Archivos a tocar (ruta real | acción | est. líneas)

| Ruta | Acción | Est. líneas |
|---|---|---|
| `agency/migrations/014_competitor_accounts.sql` | Crear | ~25 |
| `agency/backend/db/models.py` | Modificar (`CompetitorAccount`) | ~15 |
| `agency/backend/routers/competitors.py` | Crear (CRUD manual + trigger ingestión) | ~70 |
| `agency/backend/services/competitor_ingest.py` | Crear (SearXNG + extractor + index Qdrant) | ~85 |
| `agency/backend/services/rag_context.py` | Modificar (extender `index_winning_pattern` con `source`; `get_winning_patterns` filtro `source`) | ~25 |
| `agency/backend/routers/rag.py` | Modificar (endpoint `GET /{tenant}/rag/benchmark`) | ~55 |
| `agency/tests/unit/test_competitor_ingest.py` | Crear | ~60 |
| `agency/tests/unit/test_competitor_benchmark_api.py` | Crear | ~55 |
| **Total** | | **~390** |

### Contratos (endpoints/columnas/firmas)

- **Migración `014_competitor_accounts.sql`**:
  ```sql
  CREATE TABLE IF NOT EXISTS competitor_accounts (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
      platform TEXT NOT NULL DEFAULT 'instagram',
      username TEXT NOT NULL,
      display_name TEXT,
      niche TEXT,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  CREATE INDEX IF NOT EXISTS idx_competitor_accounts_tenant ON competitor_accounts (tenant_id, is_active);
  ```
- **API** (`routers/competitors.py`, prefijo `/api/v1/tenants/{tenant_id}`):
  - `GET /competitors` · `POST /competitors` `{platform, username, display_name, niche}` · `PATCH /competitors/{id}` (toggle `is_active`).
  - `POST /competitors/{id}/ingest` → dispara ingestión (manual).
- **Servicio** `competitor_ingest.py`:
  ```python
  async def ingest_competitor(account: CompetitorAccount) -> int  # nº de hooks indexados
  # asearxng_search_sanitized(f"{username} {niche} gancho viral", num_results=5)  # cache 6h existente
  # extract_hook_structure(title, snippet) -> {"title", "hook", "structure"}  # heurística + LLM opcional
  # index_winning_pattern(tenant, pattern_text, viral_score, niche, source="competitor", account_id=...)
  ```
- **rag_context** (extensión aditiva):
  ```python
  def index_winning_pattern(tenant_id, pattern_text, viral_score, niche="", source="own", account_id=None) -> bool
  # payload += {"source": source, "account_id": account_id}  # "own" = compat con analytics_agent
  def get_winning_patterns(niche="", query="", limit=3, source=None) -> list  # filtro opcional
  ```
- **Endpoint benchmark** (`GET /{tenant}/rag/benchmark?niche=X&limit=5`):
  ```json
  {"own_hooks": [...], "competitor_hooks": [...], "top_similar": [...], "gaps": ["estructuras presentes en competidores y ausentes en propias"]}
  ```

### Flujo (paso a paso numerado)

1. Migración crea `competitor_accounts`.
2. Usuario crea cuentas manualmente (`POST /competitors`) o activa/desactiva (`PATCH`).
3. `POST /competitors/{id}/ingest` → `competitor_ingest.ingest_competitor`: SearXNG (cache 6h) → extractor de estructura → `index_winning_pattern(..., source="competitor")` en Qdrant con hash 384-d.
4. `GET /{tenant}/rag/benchmark`: hooks propios (`source="own"` o ausente) vs ajenos (`source="competitor"` + solo `account.is_active=true`) → top-N por similitud + gap analysis.
5. Cuentas inactivas excluidas (filtro por `is_active` al indexar/consultar).

### Decisiones técnicas (cada una con justificación 1-2 líneas)

| Decisión | Justificación |
|---|---|
| Reusar `asearxng_search_sanitized` + su cache 6h | Patrón existente; sin scraping agresivo (riesgo ToS de la proposal). |
| Extender `index_winning_pattern` con `source` (default `"own"`) | REQ-COMP-03 exige mismo hash 384-d; aditivo, no rompe `analytics_agent` (nombrado `source` en payload). |
| Ingestión manual + trigger explícito | REQ-COMP-02; sin jobs automáticos de scraping (non-goal). |
| Filtro `is_active` al indexar/consultar | REQ-COMP-04 escenario 2: cuenta inactiva excluida. |
| Gap analysis determinista por estructura | Comparación simple de conjuntos de `structure` — testable sin LLM. |

### Estimación total + riesgo budget

~390 líneas. Riesgo budget: **Medio** (roza 400). Si el extractor con LLM creciera, partir S4a catálogo+ingestión / S4b benchmark endpoint.

---

## S5 — Reportes PDF (P5)

### Arquitectura (patrón)

Generador que devuelve **bytes PDF reales** (`weasyprint`, fallback `reportlab` si `libpango` no está en el contenedor — riesgo documentado). Datos reales: `video_metrics`, `leads` (S1), `videos`. Gráficos **SVG embebidos** (barras/lineas) generados a string. ROI con `cost_per_video_usd` configurable en tenant (default 5 USD). `metrics.py` responde `Response` binaria con `%PDF`. Frontend analytics: botón descarga.

### Archivos a tocar (ruta real | acción | est. líneas)

| Ruta | Acción | Est. líneas |
|---|---|---|
| `agency/migrations/015_tenant_cost_per_video.sql` | Crear (`tenants.cost_per_video_usd`) | ~10 |
| `agency/backend/db/models.py` | Modificar (`Tenant.cost_per_video_usd`) | ~4 |
| `agency/backend/reports/pdf_generator.py` | Modificar (rewrite → bytes; KPIs reales; gráficos SVG; ROI) | ~135 |
| `agency/backend/reports/chart_svg.py` | Crear (helpers SVG: bar/line) | ~50 |
| `agency/backend/routers/metrics.py` | Modificar (`/reports/monthly-pdf` → `Response` binaria) | ~25 |
| `agency/frontend/src/app/analytics/page.js` | Modificar (botón "Descargar PDF" + KPIs desde `/metrics` reales) | ~35 |
| `requirements.txt` (raíz) | Modificar (+`weasyprint`; fallback `reportlab`) | ~2 |
| `agency/tests/unit/test_pdf_generator.py` | Crear | ~75 |
| `agency/tests/unit/test_monthly_pdf_endpoint.py` | Crear | ~55 |
| **Total** | | **~391** |

### Contratos (endpoints/columnas/firmas)

- **Migración `015_tenant_cost_per_video.sql`**:
  ```sql
  ALTER TABLE tenants ADD COLUMN IF NOT EXISTS cost_per_video_usd NUMERIC(10,2) NOT NULL DEFAULT 5.00;
  ```
- **Generador**:
  ```python
  def generate_tenant_pdf_report(tenant_id: str, metrics_summary: dict, leads_count: int,
                                 qualified_leads: int, videos_count: int, cost_per_video_usd: float) -> bytes
  # KPIs: total_views, videos_analyzed, avg_ratio_relativo, distribution (REALES, no hardcoded)
  # charts: svg.bar_chart(distribution), svg.line_chart(views por video top-N)
  # ROI: investment = cost_per_video_usd * videos_count
  #      est_return = qualified_leads * ASSUMED_LEAD_VALUE (constante configurable, default 50 USD)
  #      roi_pct = (est_return - investment) / investment
  # weasyprint.HTML(string=html).write_pdf() ; except ImportError/libpango -> reportlab platypus
  ```
- **Endpoint** `GET /{tenant}/reports/monthly-pdf` → `Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="viralsync_report_{tenant}.pdf"'})`. Body empieza con `%PDF` (REQ-PDF-02). El comportamiento metadata-JSON queda reemplazado (rollback: mantener ruta auxiliar `/reports/monthly-pdf/meta` si hace falta hasta verify).
- **Frontend** analytics: botón "Descargar PDF" → `fetch(.../reports/monthly-pdf)` → `blob` → `URL.createObjectURL` → `<a download>`. KPIs de tarjetas pasan a consumir `/metrics` reales.

### Flujo (paso a paso numerado)

1. Migración agrega `cost_per_video_usd` (default 5).
2. `GET /{tenant}/reports/monthly-pdf` → `get_metrics_72h` (existente) + conteos de `leads`/`videos` reales + `cost_per_video_usd` del tenant.
3. `generate_tenant_pdf_report` arma HTML → SVG charts → weasyprint (fallback reportlab) → bytes.
4. Respuesta binaria `application/pdf` (REQ-PDF-02). Sin leads → sección vacía, sin error (REQ-PDF-01 escenario 2).
5. Frontend `/analytics`: botón descarga el PDF; KPIs reales (sin 0.84/48 hardcodeados).

### Decisiones técnicas (cada una con justificación 1-2 líneas)

| Decisión | Justificación |
|---|---|
| weasyprint con fallback reportlab | Riesgo `libpango` en docker (proposal); degradación limpia sin cambiar contrato de bytes. |
| Gráficos SVG (no matplotlib) | Sin dependencia pesada ni fuentes de imagen; SVG embebe limpio en weasyprint y es testable como string. |
| ROI: `cost_per_video_usd` por tenant (default 5 USD) + valor de lead constante | Decisión de usuario (P5): costo configurable; `ASSUMED_LEAD_VALUE` constante explícita y ajustable. |
| KPIs desde `video_metrics`/`leads`/`videos` reales | REQ-PDF-01: sin números hardcodeados. |
| `Content-Disposition: attachment` | REQ-PDF-04: fuerza descarga en el navegador. |
| Ruta metadata como fallback hasta verify | Rollback de la proposal: no romper consumidores hasta validar PDF binario. |

### Estimación total + riesgo budget

~391 líneas. Riesgo budget: **Medio** (roza 400). Si weasyprint + charts + endpoint sumaran, partir S5a generador+charts+ROI / S5b endpoint+frontend.

---

## Orden de implementación (resumen)

S1 (leads, desbloquea datos para S5) → S2 (independiente) → S3 (independiente) → S4 (independiente) → S5 (depende de S1 para leads reales). Encadenados vía PR chain; cada slice con revert limpio (migraciones reversibles, `beat_schedule` desregistrable, endpoints nuevos). Sub-slices solo si excede 400: **S2a/S2b** (único que lo excede hoy), S1a/S1b, S3a/S3b, S4a/S4b, S5a/S5b como planes de contingencia.

## Riesgos transversales y mitigaciones

| Riesgo | Prob. | Mitigación |
|---|---|---|
| `leads.video_id NOT NULL` rompe INSERT de webhook | Alta (hallazgo) | `DROP NOT NULL` en migración 011 + test de persistencia sin video. |
| `dm_graph` wiring con Qdrant/LLM offline rompe persistencia | Med | Best-effort: try/except → fallback `classify_intent`; persistencia nunca bloqueada. |
| S2 excede 400 líneas | Alta | Partición S2a (backend+API) / S2b (frontend+render) encadenados. |
| Duplicación publish env-vs-tenant | Med | `publisher_task` delega al micro `:8002` con credenciales tenant-first; grafo intacto. |
| Best-time Gemini (costo/latencia) | Med | Prompt acotado + timeout + fallback heurístico persistido (`source` en `best_time_slot`). |
| weasyprint/libpango ausente en docker | Med | Fallback reportlab en el mismo generador + lockfile `requirements.txt`. |
| Webhook sin scoping tenant | Med | Resolución account→tenant por `instagram_business_account_id`; SSE al tenant resuelto. |
| Idempotencia webhook (redelivery Meta) | Med | `dedup_hash` UNIQUE (sha256 user+message). |
| Migraciones fuera de orden vs numeración 011 | Baja | Numeración por orden de implementación S1→S5 (011–015), idempotentes (`IF NOT EXISTS`). |
| Threat matrix (shell/subprocess) | N/A | No se introducen boundaries de routing/shell/subprocess: `publisher_task` usa HTTP al micro, beat es config declarativa Celery, JSON2Video es HTTP. No aplica. |

## Open questions

- [ ] Confirmar valores de `locale_voices` (voces en) para las 3 personas al aplicar (especificados como propuesta en 012).
- [ ] Valor de `ASSUMED_LEAD_VALUE` para ROI (propuesto 50 USD) — confirmar en tasks/apply.
- [ ] `GET /{tenant}/rag/benchmark` filtro por nicho default: "General" (alineado con `/rag/hooks`).
