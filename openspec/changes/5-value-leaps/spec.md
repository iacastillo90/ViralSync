# Requirements: 5-value-leaps

Delta spec for the five value-leap slices (S1 DM Leads CRM → S5 PDF Reports). Order: S1=P3, S2=P2, S3=P1, S4=P4, S5=P5. All scenarios are testable; each requirement tags its test level (unit / integration).

## Requirements

**S1 — DM Leads CRM (P3)**

### REQ-DM-LEAD-01: Webhook persists Lead with tenant resolution
The system MUST persist an Instagram webhook lead as a `Lead` row (username, message, platform=instagram, status) asynchronously, resolving the tenant from the account→tenant mapping instead of the default tenant.
**Test**: integration
#### Scenario: IG comment with AUDIO keyword creates qualified lead
- **Given** a verified Instagram webhook payload containing a comment with the keyword `AUDIO` for an account mapped to a tenant
- **When** the webhook is processed by the worker
- **Then** a `Lead` is inserted with the resolved tenant, `platform=instagram`, `status=Calificado` and `qualification_score>=60`
#### Scenario: Tenant resolved non-default
- **Given** a webhook payload for an account mapped to tenant `tenant_b`
- **When** the lead is persisted
- **Then** the lead's `tenant_id` equals `tenant_b`, not the default

### REQ-DM-LEAD-02: Qualification schema migration
The system MUST add an integer `qualification_score` column to `leads` and a database index on `leads.status` via migration.
**Test**: unit
#### Scenario: Migration applies cleanly
- **Given** the pre-migration schema without `leads.qualification_score`
- **When** the migration runs
- **Then** `leads.qualification_score` (integer) exists and an index on `status` is created

### REQ-DM-LEAD-03: Keyword + intent scoring
The system MUST compute a `qualification_score` (0–100) from message keywords and classified intent (`purchase_intent`/`objection`/`question`/`spam`) and set status `Nuevo`/`Contactado`/`Calificado` accordingly.
**Test**: unit
#### Scenario: High-intent lead qualified
- **Given** a message classified `purchase_intent` with pricing keywords
- **When** scoring runs
- **Then** the lead is `Calificado` with `qualification_score>=60`
#### Scenario: Spam scored low
- **Given** a message classified `spam` with no qualifying keywords
- **When** scoring runs
- **Then** the lead is `Nuevo` with `qualification_score<30`

### REQ-DM-LEAD-04: dm_graph wiring with persisted classification
The system MUST execute the dm_graph classification for persisted leads and store the classification output in `leads.conversacion_history`.
**Test**: integration
#### Scenario: Classification available after wiring
- **Given** a persisted lead awaiting classification
- **When** the dm_graph runs against it
- **Then** the intent classification is written into `conversacion_history` of that lead

### REQ-DM-LEAD-05: Webhook idempotency
The system MUST NOT insert a duplicate `Lead` when the same (user, message) combination is received more than once, keyed by a deterministic content hash.
**Test**: unit + integration
#### Scenario: Repeated webhook does not duplicate
- **Given** an existing lead created from user+message `M`
- **When** a webhook with the same user+message `M` arrives again
- **Then** no new lead row is inserted and the original lead is returned

### REQ-DM-LEAD-06: DM send remains gated
The system MUST NOT change `node_send_dm_reply` behavior and MUST NOT simulate a DM send; S1 only persists, scores, and wires.
**Test**: unit
#### Scenario: No send side-effects
- **Given** a lead that completed S1 processing
- **When** the send node is invoked
- **Then** no Graph API messaging call is made and no simulated `pending_manual` state is produced

**S2 — Voice Personas (P2)**

### REQ-VOICE-01: Voice personas catalog
The system MUST provide a `voice_personas` table (id, name, description, edge_tts_voice, json2video_voice, is_active) seeded with the 3 confirmed personas (Masculina Enérgica, Femenina Corporativa, Fundador Tech).
**Test**: unit + integration
#### Scenario: Seed returns 3 active personas
- **Given** a fresh database
- **When** the personas are listed
- **Then** exactly the 3 confirmed personas are returned, all `is_active=true`, each with both `edge_tts_voice` and `json2video_voice` set

### REQ-VOICE-02: Renderer uses persona voice from script
The system MUST render Edge-TTS audio using the voice persisted on the script (per-scene `tts_voice`), instead of the hardcoded default.
**Test**: integration
#### Scenario: Script persona drives renderer voice
- **Given** a script whose scenes carry a persona's `edge_tts_voice`
- **When** the renderer generates speech
- **Then** the audio is produced with that persona's voice, not `es-MX-JorgeNeural` by default

### REQ-VOICE-03: json2video client parametrized
The system MUST pass the persona's `json2video_voice` to the json2video client instead of the hardcoded `es-MX-JorgeNeural`.
**Test**: unit
#### Scenario: Azure voice parameterized
- **Given** a script assigned to a persona with `json2video_voice=X`
- **When** the json2video client builds the job payload
- **Then** the payload contains `voice="X"`

### REQ-VOICE-04: Persona listing endpoint and frontend selector
The system MUST expose an endpoint listing personas and MUST provide a persona selector in the Scriptwriting frontend (and PublishApproval when applicable) that updates the script's persona.
**Test**: integration
#### Scenario: Select persona updates script
- **Given** a script and the personas endpoint
- **When** a user selects persona `P` in the selector
- **Then** the script persists `P` as its active persona

### REQ-VOICE-05: Translate→render preserves persona with target-language voice
The system MUST keep the persona on a translated script (`keyword=LANG:XX`) and MUST render that script with a target-language voice matching the persona.
**Test**: integration
#### Scenario: Translated script renders in English voice
- **Given** a script translated to `LANG:EN` with persona `P` whose voice maps to an English Edge-TTS voice
- **When** the translated script is rendered
- **Then** Edge-TTS uses the English voice for that persona

**S3 — Auto-Publishing (P1)**

### REQ-PUB-01: Video platform column
The system MUST add a `videos.platform` varchar column defaulting to `'instagram'` via migration.
**Test**: unit
#### Scenario: Migration adds platform
- **Given** the pre-migration `videos` schema
- **When** the migration runs
- **Then** `videos.platform` exists with default `'instagram'`

### REQ-PUB-02: Unified PublisherFactory
The system MUST unify publishing through a PublisherFactory that delegates to the publisher microservice (`:8002`) using its platform adapters (Instagram/TikTok/YouTube).
**Test**: unit
#### Scenario: Factory routes by platform
- **Given** a video with `platform='tiktok'`
- **When** the factory resolves a publisher
- **Then** a `TikTokPublisher` adapter is selected

### REQ-PUB-03: Celery registration and beat schedule
The system MUST register `auto_publish_scheduled_videos_task` in `celery_app.include` and MUST schedule it via `beat_schedule` (daily, configurable).
**Test**: unit
#### Scenario: Task discoverable and scheduled
- **Given** celery app configuration
- **When** the app is inspected
- **Then** the task is in the include list and a daily beat entry exists

### REQ-PUB-04: Scheduled task publishes approved videos idempotently
The system MUST have the task publish approved, unpublished videos respecting `platform`, via the factory, marking each with `published_at` and `instagram_post_id`, and MUST NOT re-publish on re-execution.
**Test**: integration
#### Scenario: Approved Instagram video published
- **Given** an approved video with `platform='instagram'` and no `published_at`
- **When** the task runs
- **Then** the video is published via the Instagram adapter and `instagram_post_id` + `published_at` are persisted
#### Scenario: Re-execution does not re-publish
- **Given** a video already published (`published_at` set)
- **When** the task runs again
- **Then** the publisher is not called for that video

### REQ-PUB-05: Best-time slot suggestion with LLM and fallback
The system MUST suggest best publish slots (day/hour) per tenant using Gemini (LLM) over `video_metrics`, falling back to historical-peak heuristics when the LLM fails.
**Test**: unit + integration
#### Scenario: LLM slot persisted
- **Given** Gemini returns a suggested slot for a tenant
- **When** best-time runs
- **Then** the suggested slot is persisted for that tenant
#### Scenario: LLM failure falls back to heuristic
- **Given** the LLM call fails or times out
- **When** best-time runs
- **Then** a slot from the historical-peak heuristic is returned and persisted

### REQ-PUB-06: Schedule endpoint triggers real scheduling
The system MUST have `POST /calendar/schedule` create a calendar record and schedule the actual beat-based publication (not only mark approval).
**Test**: integration
#### Scenario: Schedule POST creates record and beat
- **Given** a video and a chosen schedule time
- **When** `POST /calendar/schedule` is called
- **Then** a calendar record is created, the video is approved for publishing, and the beat scheduler is armed with that platform

### REQ-PUB-07: Credentials tenant-first with env fallback
The system MUST use per-tenant Instagram credentials when present and fall back to environment tokens otherwise, without breaking existing publish paths.
**Test**: unit
#### Scenario: Tenant tokens preferred
- **Given** a tenant with `instagram_graph_api_token_ref` set
- **When** the factory builds credentials
- **Then** the tenant token is used; a tenant without tokens falls back to env values

**S4 — Competitor Benchmark (P4)**

### REQ-COMP-01: Competitor accounts catalog
The system MUST provide a `competitor_accounts` table (id, tenant_id, platform, username, display_name, niche, is_active).
**Test**: unit
#### Scenario: Account creation persists
- **Given** a tenant and a competitor username
- **When** the account is created via the ingestion endpoint
- **Then** the account row exists with the given tenant/platform/niche

### REQ-COMP-02: Manual ingestion and SearXNG trends
The system MUST support manual competitor account creation and MUST ingest competitor hook trends via SearXNG with a 6-hour cache.
**Test**: integration
#### Scenario: SearXNG ingestion indexes competitor hook
- **Given** a configured competitor account and SearXNG results (cached ≤6h)
- **When** ingestion runs
- **Then** a hook entry is indexed in Qdrant with `source=competitor`

### REQ-COMP-03: Hook structure extraction and indexing
The system MUST extract hook structure (title/hook/structure) from available competitor data and index it in Qdrant `marketing_brain` with `source=competitor`, using the same 384-dimensional hash as `rag_context`.
**Test**: integration
#### Scenario: Structure indexed with competitor source
- **Given** competitor content available for a niche
- **When** the extractor indexes it
- **Then** Qdrant contains a `source=competitor` vector using the rag_context 384-d hash

### REQ-COMP-04: Benchmark endpoint
The system MUST provide `GET /{tenant}/rag/benchmark` comparing own hooks vs competitor hooks (top-N by similarity plus gap analysis).
**Test**: integration
#### Scenario: Benchmark returns comparison
- **Given** indexed own hooks and competitor hooks for a tenant
- **When** the benchmark endpoint is called
- **Then** it returns top-N similar competitor hooks and identified gaps
#### Scenario: Inactive account excluded
- **Given** an inactive competitor account
- **When** the benchmark is computed
- **Then** content from that account is not included

**S5 — PDF Reports (P5)**

### REQ-PDF-01: Real binary PDF generation
The system MUST generate a real binary PDF (weasyprint, with reportlab fallback when libpango is unavailable) containing KPI metrics from `video_metrics`, real leads (S1), videos, SVG charts, and an ROI section — no hardcoded KPIs.
**Test**: unit + integration
#### Scenario: KPIs reflect real data
- **Given** a tenant with actual `video_metrics`, `leads`, and `videos` rows
- **When** the generator runs
- **Then** the PDF embeds those real values, not hardcoded numbers
#### Scenario: No leads produces empty section
- **Given** a tenant with zero leads
- **When** the generator runs
- **Then** the PDF is produced with an empty leads section and no error

### REQ-PDF-02: Monthly PDF binary response
The system MUST have `GET /{tenant}/reports/monthly-pdf` respond with binary PDF bytes and `content_type: application/pdf` (the metadata-JSON behavior is replaced).
**Test**: integration
#### Scenario: Endpoint returns PDF bytes
- **Given** a tenant with reportable data
- **When** `GET /{tenant}/reports/monthly-pdf` is called
- **Then** the response body starts with `%PDF` and the content type is `application/pdf`

### REQ-PDF-03: Configurable ROI
The system MUST compute ROI from a per-tenant configurable cost-per-video (default 5 USD): investment = cost × videos, estimated return based on qualified leads.
**Test**: unit
#### Scenario: Custom cost drives ROI
- **Given** a tenant with cost-per-video configured to `C` and `N` videos
- **When** ROI is calculated
- **Then** investment equals `C × N` and the return uses qualified leads

### REQ-PDF-04: Frontend download button
The system MUST provide a "Descargar PDF" button on the `/analytics` page that downloads the monthly PDF report.
**Test**: integration
#### Scenario: Button downloads PDF
- **Given** the `/analytics` page for a tenant
- **When** the user clicks "Descargar PDF"
- **Then** the browser downloads a `application/pdf` file with the monthly report

## Capabilities / Affected areas

- New: `dm-lead-crm` (S1), `voice-personas` (S2), `scheduled-publishing` (S3), `competitor-benchmark` (S4).
- Modified: `sprint-2-bot-dm-rag-handoff` (REQ-DM-02 wiring, gated send — S1), `sprint-4-pdf-roi-reports` (REQ-REP-01: metadata dict → binary PDF — S5).
- Affected: `webhooks/instagram_inbound.py`, `leads.py`, `dm_graph.py`, `dm_response.py` (S1); `renderer/app.py`, json2video client, Scriptwriting/PublishApproval frontend (S2); `celery_app.py`, `publisher_task.py`, `publisher/adapters.py`, `models.py` + migration 011, `calendar.py` (S3); `rag_context.py`, `rag.py`, new ingestion (S4); `pdf_generator.py`, `metrics.py`, analytics frontend (S5).

## Acceptance Criteria

- 26 requirements across 5 slices, each with ≥1 Given/When/Then scenario and an explicit test level (unit/integration).
- Every scenario maps to a pytest test (red-green) in the `agency/tests/` suite; no scenario describes UI-only or untestable behavior.
- Non-goals enforced: no simulated DM send (S1), no ElevenLabs (S2), no graph write-path migration (S3), no full scraping/OAuth (S4), real `%PDF` bytes (S5).
