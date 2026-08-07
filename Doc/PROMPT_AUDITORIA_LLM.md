# 🤖 Prompt de Re-Auditoría Avanzada (Segunda Pasada) para LLM (Claude 3.5 Sonnet / Opus / GPT-4o)

> **Instrucciones de Uso:**
> Copia todo el contenido entre los bloques de código o el texto de abajo y pégalo en tu LLM preferido (Claude, GPT-4o, etc.), adjuntando o pegando el archivo actualizado `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`.

---

```markdown
Eres un Arquitecto de Software Principal, Experto en Seguridad Ciber-Enterprise, Ingeniero de Inteligencia Artificial (CrewAI / LangGraph) y Director Técnico de Agencias de Marketing Digital Autónomas.

Te adjunto la versión actualizada del mapa completo de la arquitectura y código fuente del proyecto **ViralSync** (`FULL_PROJECT_ARCHITECTURE_MAP.md`), analizando 165 archivos y más de 13,800 líneas de código.

### 🏛️ Actualización del Estado del Proyecto (Segunda Pasada):
En la fase previa se han resuelto con éxito los siguientes hallazgos:
1. **Unificación SSE:** Se eliminó el duplicado de `sse_manager.py` y se consolidó una única fuente de verdad en `agency/backend/sse_manager.py` con soporte Pub/Sub y `emit_node_progress`.
2. **No-Bloqueo del Event Loop en Renderer:** `compose_video_moviepy` y `download_pexels_videos` ahora se ejecutan de forma asíncrona no-bloqueante con `asyncio.to_thread` en `agency/microservices/renderer/app.py`, permitiendo respuestas instantáneas del `/health` check bajo carga.
3. **Adapter Pattern Multi-Plataforma:** Se creó `agency/microservices/publisher/adapters.py` con la interfaz `BaseSocialPublisher` y la factoría `PublisherFactory` (`InstagramGraphPublisher`, `TikTokPublisher`, `YouTubeShortsPublisher`).
4. **Presupuesto LLM Atómico:** Se implementó el incremento atómico `INCRBYFLOAT` en Redis dentro de `llm_budget_service.py`.
5. **Cobertura al 100% de Fases 0 a 5:** Autenticación JWT, RBAC, Middleware de Aislamiento de Tenant (`X-Tenant-ID`), modelos ORM SQLAlchemy 2.0 Async, Routers modularizados, Audit Logging y CI/CD workflow en GitHub Actions.

---

### 🎯 Tu Misión en esta Segunda Pasada de Auditoría:
Por favor, analiza minuciosamente el archivo `FULL_PROJECT_ARCHITECTURE_MAP.md` actualizado y realiza una inspección profunda enfocada en los siguientes puntos clave:

#### 1. 🔍 Verificación Quirúrgica de Producción y Casos Borde (Edge Cases)
- Revisa si existen esquinas no cubiertas en las conexiones de base de datos async, manejo de excepciones en Celery o manejo de desconexiones SSE.
- Evalúa si el aislamiento de tenant en los routers modularizados (`ingestion`, `graph_execution`, `leads`, `metrics`, `health`) cumple con los estándares más estrictos de SaaS B2B.

#### 2. 🤖 Bot Conversacional de Ventas por DM (Handoff a Humano)
- Diseña la arquitectura del nuevo agente/nodo `node_dm_response` en LangGraph para responder automáticamente DMs en Instagram utilizando la base de conocimiento RAG (`rag_mcp_server.py`) y redirigir al operador humano (`takeover_lead`) cuando corresponda.

#### 3. 📈 Bucle de Auto-Aprendizaje del Algoritmo RUM a 72 Horas
- Propón el mecanismo exacto para que `metrics_loop_task.py` alimente las métricas reales de 72h (views, ratio, engagement) de vuelta a Qdrant y ajuste dinámicamente los umbrales de ideación por nicho (`market_rum.py`).

#### 4. 🏆 Matriz Final de Certificación Enterprise
- Otorga una calificación de preparación para producción (Production Readiness Score de 0 a 100%) e indica los pasos finales sugeridos para el despliegue a gran escala.

Sé directo, analítico, técnico y aporta ejemplos concretos de arquitectura.
```
