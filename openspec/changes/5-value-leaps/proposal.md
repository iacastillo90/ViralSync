# Proposal: 5-value-leaps — ViralSync Value Leaps

- **id**: `5-value-leaps`
- **title**: 5 Value Leaps — Scheduled Auto-Publish, Voice Personas, DM Leads CRM, Competitor Benchmark, PDF Reports
- **summary**: Entregar 5 saltos de valor en 5 PRs encadenados (≤400 líneas c/u): auto-publicación agendada real, voces multi-idioma, leads persistidos + DM real, benchmark de competidores, reportes PDF reales.

## Problem

El producto tiene 5 capacidades incompletas/dead code: (1) `publisher_task.py` agendado nunca corre; (2) voz hardcodeada, sin selector ni doblaje por idioma; (3) leads NUNCA se persisten y el DM no se envía; (4) cero visibilidad de competidores; (5) reporte PDF devuelve JSON, no bytes.

## Why (evidencia de exploración)

- P1: `auto_publish_scheduled_videos_task` NO está en `celery_app.include` (solo video_edit/metrics_loop/webhook_dlq/trend_scraper/graph_execution/rum_learning) ni hay `beat_schedule` → dead code. Microservicio publisher (:8002) vivo con adapters (InstagramGraphPublisher 2 pasos + polling, TikTok, YT Shorts) usado por el grafo.
- P2: renderer Edge-TTS con `DEFAULT_VOICE=es-MX-JorgeNeural` + `tts_voice` por escena; `json2video_client.py` hardcodea `voice="es-MX-JorgeNeural"`; `POST /scripts/{id}/translate` crea Script nuevo (`keyword=LANG:XX`) pero el render sigue con voz fija. Cero ElevenLabs (grep confirmado).
- P3: `POST /webhooks/instagram` con HMAC + verify token + DLQ; `instagram_inbound.py` extrae leads por keyword y emite SSE `lead_captured`; `dm_graph.py`+`dm_response.py` (clasificación purchase_intent/objection/question/spam, RAG, budget guard) existen pero NO se cablean al webhook; tabla `leads` completa. **Cero `INSERT Lead` en runtime** (grep: solo modelo + seed de test) → `get_tenant_leads` siempre vacío. `node_send_dm_reply` solo loguea+SSE.
- P4: RAG propio (`rag_context.py` → Qdrant `marketing_brain`, hash 384-d) alimentado solo con ganchos propios (analytics_agent, viral_score≥0.35); `searxng_mcp_server.py` (cache Redis 6h) para tendencias. Cero referencias a competidores en el repo.
- P5: `pdf_generator.py` devuelve SOLO dict de metadatos (`content_type: application/pdf` falso); `/reports/monthly-pdf` responde JSON; sin librería PDF ni gráficos; KPIs hardcodeados en `/analytics`; datos reales disponibles (video_metrics, leads, videos).

## Success Metrics

- P1: `auto_publish_scheduled_videos_task` registrado + beat schedule; videos con `platform` persistida; slots best-time sugeridos por **LLM Gemini** (decisión usuario).
- P2: catálogo `voice_personas` con **3 personas confirmadas** + selector en frontend; render por idioma con voz correcta (traducción→render).
- P3: webhook persiste `Lead` (status Nuevo/Contactado/Calificado + `qualification_score`); dm_graph cableado. El **envío real del DM queda GATEADO hasta tener app Meta de producción** (decisión usuario); sin envío simulado.
- P4: `GET /{tenant}/rag/benchmark` compara propios vs ajenos (`source=competitor`).
- P5: `/reports/monthly-pdf` devuelve PDF binario real (weasyprint) con gráficos y ROI (costo configurable); botón descarga en `/analytics`.
- Todos los slices con tests red-green (pytest).

## Non-Goals

- NO ElevenLabs real (sin key) — solo Edge-TTS + voces Azure de json2video.
- NO envío real de DM sin app Meta de producción: S1 persiste leads + scoring + wiring dm_graph; el envío IG Messaging queda gateado (decisión usuario — no simular `pending_manual`).
- NO scraping completo de redes sociales — cuentas configuradas manualmente + tendencias SearXNG.
- NO clonado/entrenamiento de voz, NO generación de video, NO OAuth tokens (diferido, ver api-publish-wiring).
- NO migrar el path de publish del grafo existente.

## Implementation Approach — 5 slices encadenados (force-chained, 400 líneas/slice)

Orden por dependencias: P3 primero (desbloquea datos de leads para P5); P1/P2/P4 independientes; P5 último (consume leads reales).

| # | Slice | Depende de | Estimación (aprox.) | Nota budget |
|---|-------|-----------|---------------------|-------------|
| S1 | **P3 DM Leads CRM**: webhook→persistir Lead (worker), migración `leads.qualification_score`, scoring (keywords+intención→Nuevo/Contactado/Calificado), cablear dm_graph. Envío real GATEADO hasta app Meta prod | — | ~310 (persist 80, migración 40, scoring 60, wiring 60, tests 70) | Riesgo medio; sin envío simulado |
| S2 | **P2 Voice Personas**: tabla `voice_personas` + seed (3 personas confirmadas), parametrizar voice en renderer/json2video, selector frontend (Scriptwriting/PublishApproval), flujo traducir→render | — | ~400 (tabla 60, param 50, frontend 80, flujo 60, tests 150) | |
| S3 | **P1 Auto-Publicación**: migración `videos.platform` (011), unificar vía PublisherFactory (delega al microservicio), registrar en celery include + beat_schedule, best-time con **LLM Gemini** | — | ~400 (migración 40, factory 80, celery 30, best-time 80, tests 170) | |
| S4 | **P4 Competitor Benchmark**: tabla `competitor_accounts` + ingestión manual/SearXNG, extractor estructura de ganchos → Qdrant `source=competitor`, `GET /rag/benchmark` | — | ~400 (tabla 40, ingestión 70, extractor 70, index 40, endpoint 50, tests 130) | |
| S5 | **P5 Reportes PDF**: weasyprint, rewrite generador (bytes + gráficos SVG), `metrics.py` Response binaria, ROI con **costo por video configurable en tenant (default 5 USD)**, botón descarga en `/analytics` | S1 (leads reales) | ~400 (generador 120, charts 50, endpoint 30, ROI 40, frontend 30, tests 130) | Si weasyprint falla en docker (libpango), fallback reportlab |

Regla: si un slice supera 400 líneas, se divide en sub-slices encadenados (mismo patrón).

## Capabilities

### New
- `scheduled-publishing`: beat auto-publish unificado vía factory + `videos.platform` + best-time.
- `voice-personas`: catálogo, parametrización Edge-TTS/json2video, selector frontend, doblaje por idioma.
- `dm-lead-crm`: persistencia de leads, qualification_score, wiring dm_graph, envío IG Messaging 24h.
- `competitor-benchmark`: cuentas competidoras, ingestión, estructura de ganchos, benchmark propio vs ajeno.

### Modified
- `sprint-4-pdf-roi-reports`: REQ-REP-01 pasa de dict de metadatos a PDF binario real + gráficos + ROI con costo configurable.
- `sprint-2-bot-dm-rag-handoff`: REQ-DM-02 — la respuesta generada se ENVÍA (IG Messaging, ventana 24h) además de SSE; dm_graph cableado al webhook.

## Affected Areas

| Area | Impact |
|------|--------|
| `agency/workers/celery_app.py`, `agency/workers/publisher_task.py` | Modified (S3) |
| `agency/microservices/publisher/adapters.py`, `agency/backend/db/models.py` (+migración 011) | Modified (S3) |
| `agency/microservices/renderer/app.py`, `agency/agents/nodes/` json2video client, frontend Scriptwriting/PublishApproval | Modified (S2) |
| `agency/backend/webhooks/instagram_inbound.py`, `agency/agents/dm_graph.py`, `agency/agents/nodes/dm_response.py`, `agency/backend/routers/leads.py` | Modified (S1) |
| `agency/services/rag_context.py`, `agency/backend/routers/rag.py`, nueva ingestión | Modified (S4) |
| `agency/backend/reports/pdf_generator.py`, `agency/backend/routers/metrics.py`, `frontend analytics/page.js` | Modified (S5) |

## Risks

| Riesgo | Prob. | Mitigación |
|--------|-------|-----------|
| P1: duplicación publish (env tokens vs per-tenant) | Med | Unificar vía PublisherFactory delegando al microservicio; grafo sigue siendo único write-path |
| P1: best-time con LLM (costo/calidad) | Med | Prompt acotado a video_metrics + heurística fallback; retroalimenta con video_metrics |
| P3: envío DM real no disponible sin app Meta prod | Alta | GATEADO por decisión de usuario: S1 persiste + score + wiring; envío queda pendiente de app real |
| P3: webhook sin scoping tenant (SSE "default") | Med | Mapear cuenta→tenant al persistir lead |
| P4: scraping frágil/ToS | Med | Cuentas manuales + SearXNG cache 6h; sin scraping agresivo |
| P5: weasyprint en docker (libpango) | Med | Lockfile + verificación pipeline; fallback reportlab |
| Budget 400 líneas | Med | Sub-slices encadenados si excede |

## Rollback Plan

Cada slice es PR independiente con revert limpio: migraciones reversibles (drop columna/platform), desregistrar `beat_schedule` (P1), endpoints nuevos (benchmark, PDF binario) sin tocar rutas existentes (P5 mantiene ruta metadata como fallback hasta verify), envío DM gateado sin auto-envío real (P3). Ningún slice modifica el write-path del grafo vigente.

## Dependencies

- Existentes (pobladas): Edge-TTS, JSON2VIDEO_API_KEY, SearXNG, Qdrant, Postgres, Redis, LLM router (GEMINI/GROQ/etc.).
- Nueva: `weasyprint` (S5). NO usar: ElevenLabs, Meta prod, tokens TikTok/YT reales (placeholders).
- TDD estricto: `cd agency && ../venv/bin/python -m pytest tests/`.

## Resolved Decisions (usuario)

1. **P1 best-time**: LLM con Gemini (no histórico simple). Costo aceptado por el usuario.
2. **P2 catálogo**: 3 personas iniciales confirmadas (Masculina Enérgica, Femenina Corporativa, Fundador Tech) mapeadas a pares voice por motor (edge-tts / json2video Azure).
3. **P3 envío**: esperar app Meta de producción. S1 NO simula envío; persiste + score + wiring, y deja el envío pendiente de app real.
4. **P5 ROI**: costo por video configurable en tenant (default ~5 USD, USD).
5. **Orden de slices**: confirmado S1=P3 primero, S5=P5 último.
