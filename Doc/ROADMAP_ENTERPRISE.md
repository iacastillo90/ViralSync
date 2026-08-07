# Roadmap Enterprise — ViralSync

Este documento es la fuente de verdad del plan de desarrollo Enterprise para ViralSync. Estructura el trabajo en 6 fases secuenciales para transformar el prototipo en una plataforma SaaS B2B resiliente, segura y altamente escalable.

---

## 📊 Matriz de Fases y Cobertura

| Fase | Enfoque | Objetivo Principal | Estado Actual |
|---|---|---|---|
| **Fase 0** | Higiene y Verificación | CI/CD, pins, health checks backend, Next.js audit | 🟡 Parcial (60%) |
| **Fase 1** | Seguridad Fundacional | Auth JWT/RBAC, Tenant Isolation, Rate Limiting | 🔴 Pendiente (20%) |
| **Fase 2** | Núcleo Real de Negocio | SQLAlchemy Async, Refactor `main.py`, Grafo E2E real, RAG Multi-tenant | 🟡 Parcial (70%) |
| **Fase 3** | Resiliencia y Operaciones | SSE Durable (Redis PubSub), Containerización Backend/Workers, Backups | 🟡 Parcial (65%) |
| **Fase 4** | Observabilidad & Costos LLM | Log de Tokens LLM, Presupuesto Tenant, Frontend 100% Real | 🟡 Parcial (50%) |
| **Fase 5** | Enterprise y Escala | Feature Flags, Audit Logs, SLOs, Billing | 🔴 Pendiente (10%) |

---

## 🎯 Detalle por Fase

### Fase 0 — Higiene y Verificación (~1 semana)
- [x] Pinar dependencias en `requirements.txt`.
- [x] Health checks `/health` en microservicios `renderer` y `publisher`.
- [ ] Implementar `/health` unificado en FastAPI backend (`agency/backend/main.py`) probando conexiones DB, Redis y Qdrant.
- [ ] Configurar GitHub Actions Workflow `.github/workflows/ci.yml` con ejecución de linting y `pytest`.

### Fase 1 — Seguridad Fundacional (~1-2 semanas)
- [ ] Implementar autenticación JWT y RBAC (`agency/backend/security/auth.py`).
- [ ] Middleware de aislamiento estricto de tenants (`tenant_id` obligatorio en cada request).
- [ ] Rate limiting middleware por IP y por tenant en FastAPI.
- [ ] Validación estricta de variables de entorno al iniciar la app.

### Fase 2 — Núcleo Real de Negocio (~3-4 semanas)
- [ ] Refactorizar `agency/backend/main.py` hacia una estructura modular por routers (`backend/routers/`).
- [ ] Implementar modelos SQLAlchemy Async para Tenants, Ideas, Guiones, Leads y Métricas.
- [ ] Configurar `PostgresSaver` en `graph.py` para la persistencia real de hilos por tenant.
- [ ] Conectar la ejecución del grafo `graph_app.astream()` en el endpoint `/graph/run`.
- [ ] Aislamiento de colecciones RAG en Qdrant por `tenant_id`.

### Fase 3 — Resiliencia y Operaciones (~2 semanas)
- [ ] SSE Manager Durable basado en Redis Pub/Sub para soporte multi-instancia.
- [ ] Descomentar e integrar `backend` y `celery_worker` en `agency/docker-compose.yml`.
- [ ] Script y contenedor de respaldos automáticos de PostgreSQL (`pg_dump`).

### Fase 4 — Observabilidad, Costos LLM y Frontend (~2-3 semanas)
- [ ] Tabla `llm_usage_log` y middleware para rastrear consumo de tokens y dólares por tenant.
- [ ] Bloqueo automático de llamadas LLM al superar el presupuesto mensual asignado.
- [ ] Conectar al 100% las vistas del Dashboard Next.js con endpoints REST reales y manejo de errores.
- [ ] Logging estructurado en formato JSON y hooks de OpenTelemetry.

### Fase 5 — Enterprise y Escala (Continuo)
- [ ] Sistema de Feature Flags por tenant.
- [ ] Audit log de acciones administrativas (`audit_logs` table).
- [ ] Métricas de disponibilidad y SLOs (Service Level Objectives).

---

## 📈 Matriz de Mapeo de Deudas a Fases

| Deuda Técnica / Hallazgo | Fase Asignada |
|---|---|
| Inexistencia de CI/CD, dependencias no bloqueadas | Fase 0 |
| Falta de auth JWT / RBAC y aislamiento de tenant | Fase 1 |
| God file `main.py` sin modularizar | Fase 2 |
| Grafo no persistido en PostgresSaver real | Fase 2 |
| RAG no aislado por tenant en Qdrant | Fase 2 |
| SSE Manager en memoria sin Redis PubSub | Fase 3 |
| Backend y Celery comentados en Docker Compose | Fase 3 |
| Sin seguimiento de uso/presupuesto de tokens LLM | Fase 4 |
| Vistas del Frontend con mocks y sin error boundaries | Fase 4 |
| Sin audit log ni feature flags | Fase 5 |
