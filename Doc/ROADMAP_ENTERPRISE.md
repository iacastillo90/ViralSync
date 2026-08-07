# Roadmap Enterprise — ViralSync

**Estado:** v1.0 — derivado de auditoría completa (arquitectura, flujo, seguridad, dependencias, readiness de producción) del 2026-08-06.
**Objetivo:** llevar ViralSync a producción/enterprise cubriendo el **100%** de los hallazgos, deuda técnica, mejoras y refactorizaciones.
**Fuera de alcance (solicitud explícita del usuario):** explotación de múltiples API keys en la capa free para testing.

---

## Principios de ordenamiento

1. **Verificación antes que cambio** — CI/CD desde la Fase 0 para que todo cambio posterior esté protegido por tests.
2. **Seguridad antes que features** — no se construye sobre cimientos sin autenticación.
3. **Núcleo real antes que escala** — el grafo debe ejecutar y persistir de verdad antes de hablar de SLOs o billing.
4. **Observabilidad antes que optimización** — no se optimiza lo que no se mide.
5. **Cada fase es un hito desplegable e independiente** — se ejecuta como 1+ cambios SDD con gates de review; una fase no se cierra sin su criterio de salida.

---

## Resumen de fases

| Fase | Nombre | Foco | Duración est. |
|---|---|---|---|
| 0 | Higiene y Verificación | deps, CI, health, quick wins | 1 semana |
| 1 | Seguridad Fundacional | authN/authZ, HMAC, secretos, RLS | 1–2 semanas |
| 2 | Núcleo Real | persistencia, grafo, adapters reales, refactor | 3–4 semanas |
| 3 | Resiliencia y Operaciones | DLQ, SSE durable, deploy, backups | 2 semanas |
| 4 | Observabilidad, Costos LLM y Frontend | OTel, budgets, frontend real | 2–3 semanas |
| 5 | Enterprise y Escala | flags, audit, SLOs, billing, modernización | continuo |

---

## Fase 0 — Higiene y Verificación

**Objetivo:** repo reproducible, verificado y con quick wins aplicados. "Hacer seguro el cambio."

### Alcance
- [ ] **Upgrade Next.js 14 → 15.5.16+ (o 16.x)** y postcss → 8.5.26. Limpia 22+ advisories (SSRF CVSS 8.6, bypass de middleware, DoS) que **no tienen fix en 14.x**.
- [ ] **Pinear dependencias Python** (`==`/`~=` + lockfile con pip-tools o uv) en los 3 requirements; corregir rango inválido `crewai >=0.41.0` (latest PyPI es 0.11.2).
- [ ] **Reconciliar venv con requirements**; alinear Python local (3.11/3.12) con las imágenes Docker (hoy 3.14 vs 3.11).
- [ ] **Pinear imágenes Docker**: reemplazar `litellm:main-latest` (tag mutable de rama) por release tag; tags específicos para qdrant/searxng/ollama/minio.
- [ ] **CI/CD baseline**: GitHub Actions — pytest + gate de coverage, `npm ci && next build`, lint (ruff + ESLint), hadolint, `pip-audit` + `npm audit`.
- [ ] **`/health` + `/ready`** en backend (checks de Postgres/Redis/Qdrant).
- [ ] **CORS explícito** (lista de orígenes, sin `*` con credentials).
- [ ] **`.gitignore`: `.env*`** (hoy `.env.local` no está ignorado); secret-scan (gitleaks) en CI.
- [ ] **Alembic** sobre `001_init_schema.sql` (versión base + tabla de versiones aplicadas).
- [ ] **Prune de requirements sin uso** (crewai, llama-index, whisper, litellm, sqlalchemy — solo si no se requieren en Fase 2).
- [ ] **Corregir README** (comando uvicorn incorrecto: no existe `agency/__init__.py`).
- [ ] **`error.js` / `loading.js` / `global-error.js` / `not-found.js`** en App Router (hoy un crash = pantalla blanca).
- [ ] **Microservicios**: contenedores non-root + HEALTHCHECK + `.dockerignore` (adelanto de Fase 3).

### Criterio de salida
- `npm audit` limpio; CI verde en `main`.
- Builds reproducibles (lockfile Python + imágenes pineadas).
- Backend expone `/health` `/ready`; frontend con error boundaries mínimos.

---

## Fase 1 — Seguridad Fundacional

**Objetivo:** cero acceso anónimo, cero secrets por defecto, webhooks a prueba de bypass.

### Alcance
- [ ] **Autenticación JWT/OIDC + RBAC** (admin/operator) con FastAPI `Depends` en todas las rutas (REST, SSE, microservicios).
- [ ] **Enforcement de tenant server-side**: `tenant_id` proviene de la sesión (no del path/header), ownership check por ruta; UUIDs no predecibles (`tenant-{name}-001` hoy es enumerable).
- [ ] **Eliminar clave LiteLLM del bundle cliente** (`useTenantStore.js:8`) y la derivación predecible `sk-agency-{tenant}` (`main.py:80`); virtual keys aleatorias server-side, almacenadas hasheadas.
- [ ] **HMAC webhook obligatorio**: `main.py:311` hoy valida solo `if x_hub_signature_256:` → **401 si falta firma**, verificación antes de parsear JSON, replay protection (timestamp/nonce/idempotency), `compare_digest` en el verify token.
- [ ] **Secretos**: fail-fast si se usa un default fuera de `dev`; secrets manager (Vault/AWS SM); rotación automática del token Meta a 60 días.
- [ ] **Aislamiento de infra**: Redis AUTH/TLS; credenciales fuertes Postgres/MinIO; **red interna** (dejar de publicar 5432/6379/6333/4000/9000/11434 al host).
- [ ] **RLS en Postgres**: `ENABLE ROW LEVEL SECURITY` + policies por tenant; `litellm_virtual_key` cifrado en reposo (hoy plaintext en `tenants`).
- [ ] **Sanitización de path traversal**: `tenant_id` y filenames en `minio_client.py` y `renderer/app.py`; filenames `[a-z0-9_-]` en `trend_scraper_task.py`.
- [ ] **SSRF**: allowlist de hosts para Pexels/Shotstack/Meta; `video_url` del publisher solo permite origen propio (MinIO).
- [ ] **Rate limiting** (slowapi) + límites de tamaño (`script_text`, texto de webhook).
- [ ] **`/publish` y `/render`**: auth interna, ignorar `access_token` del cliente, errores sanitizados (sin `str(exc)`).
- [ ] **Exception handlers globales** que no filtren internals.

### Criterio de salida
- Sin endpoints anónimos (excepto `/health` y login).
- Webhook sin firma → HTTP 401 verificado por test.
- Sin credenciales por defecto utilizables fuera de dev.

---

## Fase 2 — Núcleo Real

**Objetivo:** el pipeline ejecuta de verdad: grafo persistente con checkpoints humanos, datos en Postgres, adapters reales.

### Alcance
- [ ] **Repositorios SQLAlchemy 2.0 async** sobre el esquema existente; transacciones para la cadena idea→script→video→campaign (hoy el esquema está muerto: nada lo lee/escribe).
- [ ] **Checkpointer `PostgresSaver`** en `graph.py` (hoy compila sin checkpointer → `interrupt_before` no pausa nada); `/graph/run` **invoca** el grafo (`thread_id=tenant_id`); approve/reject → `get_state`/`update_state`/`invoke` con **conditional edges** reales.
- [ ] **Refactor de `main.py`** (god file de 336 líneas): routers por dominio (tenants, pipeline, leads, metrics, webhooks) + service layer + repository layer.
- [ ] **Adapters reales**: upload MinIO real (hoy arma una URL y no sube), embeddings reales (hoy es un hash) con colección Qdrant **tenant-partitioned**, cliente Shotstack/Fal real (hoy devuelve URIs `s3://` falsas).
- [ ] **RAG tenant-namespaced**: claves Redis por tenant (hoy `rag_cache:{md5(query)}` global) + colección Qdrant por tenant.
- [ ] **Merge de los dos SSE managers** (`backend/sse_manager.py` vs `realtime/sse_manager.py` muerto); emitir eventos reales (`node_change`, `log_entry`, `checkpoint_paused`, `new_lead`) que el frontend ya espera.
- [ ] **Fix `lead_qualifier`** (import roto a `get_active_campaign_keywords`); webhook → qualifier; keyword desde tabla `campaigns` (hoy hardcodeada `"CONSULTA"`).
- [ ] **Celery real**: encolar render desde el grafo; beat schedules para `metrics_loop_task` (72h) y `trend_scraper_task` (diario).
- [ ] **Publisher**: idempotency key y guard post-poll (hoy publica aunque el status nunca llegue a FINISHED).
- [ ] **Eliminar dead code**: `realtime/sse_manager.py`, branches fake de `video_gen_client.py`, `market_rum.py` hasta su wiring, fabricaciones de IDs (`ig_reel_{tenant[:8]}_99812`), `fetchWithTenant` huérfano en frontend.
- [ ] **Extraer `simple_embedding` compartido** (duplicado en `rag_mcp_server.py` y `ingest_knowledge.py`); fixtures de contrato únicos (los mock payloads están triplicados backend/docs/frontend).
- [ ] **Valores configurables**: RUM threshold (hoy `0.050` hardcodeado contra la regla de `Agents.md`), quality `0.70`, duración 45s — a env/config.
- [ ] **Tests de integración**: Postgres/Redis/Qdrant reales; tests para ambos microservicios (hoy 0).

### Criterio de salida
- E2E real: grafo ejecutado de punta a punta con checkpoints y persistencia.
- Coverage de rutas críticas ≥ 70% (hoy `market_rum` 0%, `video_edit` 11%).

---

## Fase 3 — Resiliencia y Operaciones

**Objetivo:** sobrevive fallos parciales, no pierde datos, se despliega y se recupera.

### Alcance
- [ ] **DLQ real**: hoy `webhook_dlq_task.py:43-44` "persiste en Redis" pero solo devuelve un dict → lista Redis + replay CLI + herramientas de inspección.
- [ ] **Celery hardening**: `acks_late` para render, idempotency keys por tarea (`tenant_id:video_id`), `task_time_limit`/`soft_time_limit`, concurrencia por cola.
- [ ] **`video_edit_task.py:80-81` honesto**: `status: "failed"` cuando el render falla (hoy reporta `"completed"` con URL placeholder).
- [ ] **SSE durable**: buffer Redis + `Last-Event-ID` replay; colas acotadas con política drop-oldest (hoy colas en RAM sin límite).
- [ ] **Graceful shutdown**: `lifespan` de FastAPI para drenar SSE/DB/clients en SIGTERM.
- [ ] **Renderer sin bloqueo del event loop**: MoviePy CPU-bound corre en job/queue, no en `async def` de la request.
- [ ] **Containerizar backend + workers** (hoy comentados en compose → el sistema no es desplegable); Dockerfile non-root, HEALTHCHECK, `.dockerignore`, resource limits, red interna.
- [ ] **Backups/DR**: `pg_dump`/WAL, versioning en MinIO, snapshots de Qdrant, runbook de restore probado, RPO/RTO definidos.
- [ ] **Consistencia de env**: `.env.example` completo (hoy faltan `INSTAGRAM_GRAPH_ACCESS_TOKEN`, `PEXELS_API_KEY`, `SHOTSTACK_API_KEY`, `RENDERER_SERVICE_URL`, `MINIO_*` consumidos por código); convención única de nombres.

### Criterio de salida
- Prueba de caos (matar Redis/worker/renderer) sin pérdida de datos ni estados colgados.
- Restore probado desde backup.
- `docker compose up` = sistema completo operativo.

---

## Fase 4 — Observabilidad, Costos LLM y Frontend Real

**Objetivo:** ver qué pasa, controlar el gasto LLM, y que el frontend consuma la API de verdad.

### Alcance
- [ ] **OpenTelemetry** auto-instrumentación (FastAPI + Celery + Redis + httpx), middleware de request-ID, logs JSON estructurados, endpoint `/metrics`, Sentry.
- [ ] **Flower** + métricas de profundidad de cola; alertas de backlog.
- [ ] **Costos LLM**: poblar `llm_usage_log` (la tabla ya existe, nada la escribe) desde el spend endpoint de LiteLLM; **virtual keys por tenant con `max_budget`**; alerta cuando crece el share del fallback pagado (`was_paid_fallback`).
- [ ] **Frontend real**: conectar vistas a la API (hoy renderizan mock data hardcodeada); usar la capa `services/apiConfig.js` (hoy sin importadores); loading/error states; fetch wrapper con retry/timeout/toasts.
- [ ] **Security headers** en `next.config.js` (CSP, HSTS, X-Frame-Options, `images.remotePatterns`).
- [ ] **Env validation** (zod); **paginación cursor** en `/leads` y `/metrics` (hoy sin límites).
- [ ] **Tests frontend reales** (Vitest + React Testing Library) reemplazando los checks de existencia de archivos.

### Criterio de salida
- Dashboard opera con datos reales end-to-end.
- Traza completa request → Celery → microservicio visible en una herramienta.
- Budget LLM por tenant con alerta activa.

---

## Fase 5 — Enterprise y Escala

**Objetivo:** SLOs, facturación, feature flags y modernización técnica continua.

### Alcance
- [ ] **Feature flags** (OpenFeature/Flagsmith) para gatear nodos nuevos (publish, trend scraper) por tenant.
- [ ] **Audit log** (actor, tenant, acción, before/after) para aprobaciones humanas y takeovers — separado de `llm_usage_log`.
- [ ] **SLOs + error budgets** (tasa de completitud del grafo, latencia P95 de ingesta webhook, éxito de render) con Prometheus/Grafana.
- [ ] **API versioning + contract tests**: enforcement de `API_CONTRACTS.md` con pydantic response models / OpenAPI tests (hoy docs y código divergen).
- [ ] **Billing**: metering de uso + Stripe + quotas por tenant.
- [ ] **Modernización técnica**: MoviePy 2.x (1.x legacy), React 19, Tailwind 4, lucide 1.x, websockets/portalocker.
- [ ] **Escala**: autoscaling de workers, multi-región (read replicas Postgres, replicación MinIO, Redis multi-AZ), down-migrations de Alembic.
- [ ] **RLS refinada** con roles y revisión de aislación Qdrant a escala.

### Criterio de salida
- Sistema operado bajo SLOs definidos.
- Tenant puede pagar y consumir con quotas.
- Sin deuda técnica conocida sin plan de mitigación.

---

## Mapa de cobertura (hallazgo → fase)

| Área de hallazgo | Fase |
|---|---|
| Next.js 14 EOL / 22 advisories, postcss | 0 |
| Pins `>=`, sin lockfile, rango crewai inválido, venv desalineado | 0 |
| Imágenes Docker flotantes (`litellm:main-latest`) | 0 |
| Sin CI/CD, sin lint, sin gates | 0 |
| Sin `/health`, CORS `*`+credentials, README roto | 0 |
| `.env.local` sin ignorar, secret-scan | 0 |
| Migraciones manuales sin Alembic | 0 |
| Frontend sin error boundaries | 0 |
| Cero autenticación, IDOR por tenant, SSE público | 1 |
| HMAC opcional, replay, verify token con `==` | 1 |
| Clave LiteLLM en bundle cliente + derivación predecible | 1 |
| Defaults de secretos, Redis sin AUTH, puertos expuestos | 1 |
| Sin RLS, keys plaintext en DB | 1 |
| Path traversal (minio/renderer/trend_scraper), SSRF | 1 |
| `/publish` `/render` sin auth, `str(exc)` leaks | 1 |
| Sin rate limiting ni límites de tamaño | 1 |
| Grafo nunca invocado, sin checkpointer, sin edges condicionales | 2 |
| Esquema Postgres muerto, sin repos/transacciones | 2 |
| Adapters falsos (MinIO, Shotstack, hash embedding) | 2 |
| Cache/Qdrant globales (cross-tenant) | 2 |
| SSE managers duplicados, contratos SSE rotos | 2 |
| `lead_qualifier` roto, keyword hardcodeada, DLQ falso | 2 / 3 |
| Celery sin enqueues ni beat, publisher huérfano | 2 |
| Dead code, god file `main.py`, mocks triplicados | 2 |
| Hardcodes (RUM 0.050, quality 0.70, 45s, IDs fake) | 2 |
| Tests de microservicios ausentes, integración inexistente | 2 |
| DLQ mentiroso, `video_edit_task` "completed" falso | 3 |
| SSE no durable, sin graceful shutdown, renderer bloqueante | 3 |
| Backend/workers sin containerizar, compose incompleto | 3 |
| Sin backups/DR, sin RPO/RTO | 3 |
| Cero observabilidad (OTel/Sentry/logs JSON/metrics) | 4 |
| `llm_usage_log` sin usar, sin budgets por tenant | 4 |
| Frontend mock data, sin error/loading, sin headers de seguridad | 4 |
| Sin paginación, sin env validation | 4 |
| Sin feature flags, audit log, SLOs, billing | 5 |
| MoviePy 1.x, React 18, Tailwind 3, lucide 0.x | 5 |
| Multi-región, autoscaling, down-migrations | 5 |

---

## Cómo se ejecuta

- **Cada fase = 1+ cambios SDD** (`proposal → spec → design → tasks → apply → verify → archive`) con gates de review por cambio.
- **Dependencias entre fases**: 0 y 1 son prerrequisito de 2; 2 es prerrequisito de 3 y 4; 5 es continuo y puede solaparse con 3-4.
- **Orden dentro de fase**: por dependencia técnica; cada ítem se valida con tests antes de darse por cerrado.
- **Salida por fase**: criterio de salida verificado + actualización de `Doc/*.md` para eliminar la divergencia doc/código.
