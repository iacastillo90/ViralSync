# 🤖 Prompt de Certificación Final y Auditoría Enterprise (Tercera Pasada) para LLM (Claude 3.5 Sonnet / Opus / GPT-4o)

> **Instrucciones de Uso:**
> Copia todo el contenido entre los bloques de código de abajo y pégalo en tu LLM preferido (Claude, GPT-4o, etc.), adjuntando o pegando el archivo actualizado `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`.

---

```markdown
Eres un Arquitecto de Software Principal, Experto en Seguridad Ciber-Enterprise, Ingeniero de Inteligencia Artificial (CrewAI / LangGraph) y Director Técnico de Agencias de Marketing Digital Autónomas.

Te adjunto la versión oficial más reciente del mapa completo de la arquitectura y código fuente del proyecto **ViralSync** (`FULL_PROJECT_ARCHITECTURE_MAP.md`), analizando 168 archivos y más de 14,100 líneas de código.

### 🏛️ Actualización del Estado del Proyecto (Tercera Pasada - Estado Actual):
En las fases previas se han resuelto con éxito la totalidad de las observaciones de auditoría:

1. **Robustecimiento de Infraestructura y Resiliencia Async:**
   - `agency/backend/db/session.py`: `create_async_engine` configurado con `pool_pre_ping=True`, `pool_recycle=3600`, `pool_size=10` y `max_overflow=20` para descartar conexiones zombis en PostgreSQL.
   - `agency/workers/celery_app.py`: Activadas las banderas `task_acks_late=True` y `task_reject_on_worker_lost=True` para evitar la pérdida silenciosa de tareas pesadas de renderizado ante caídas de workers.

2. **Bot Conversacional de Ventas por DM con RAG (`agency/agents/dm_graph.py` & `dm_response.py`):**
   - Grafo compilado en LangGraph dedicado a DMs de Instagram.
   - Clasificación automática de intenciones (`question`, `objection`, `purchase_intent`, `spam`).
   - Recuperación de contexto semántico RAG desde Qdrant (`query_rag_knowledge`).
   - Cálculo del score de confianza: si es menor al 75% (`< 0.75`) o ante objeciones/intención de venta, activa automáticamente el handoff a humano (`requires_human=True`).

3. **Bucle de Auto-Aprendizaje RUM a 72 Horas (EMA + Clamp Guardia):**
   - `agency/workers/metrics_loop_task.py`: Recalibración del umbral dinámico RUM por nicho utilizando **Media Móvil Exponencial ($\alpha = 0.15$)** y actualización en Redis (`rum_threshold:{niche}`).
   - `agency/agents/criterion/rum_calculator.py`: Función `get_dynamic_threshold(niche)` con protección de **clamp guardia estricto entre `[0.50, 0.90]`** para prevenir descalibraciones por ganchos o posts virales atípicos.

4. **Aislamiento de Tenant & Prevención Anti-IDOR (`agency/backend/routers/leads.py`):**
   - Validación ineludible del `tenant_id` en las peticiones HTTP del panel de Inbound Leads y en el endpoint de takeover por parte del operador humano.

5. **Infraestructura Base Completada al 100%:**
   - Unificación única de `sse_manager.py` con Pub/Sub.
   - Event loop de FastAPI no-bloqueante en `agency/microservices/renderer/app.py` con `asyncio.to_thread(...)` y recolección estricta de basura `Zero Waste`.
   - Adapter Pattern Multi-Plataforma en `agency/microservices/publisher/adapters.py` (`InstagramGraphPublisher`, `TikTokPublisher`, `YouTubeShortsPublisher`).
   - Presupuesto LLM atómico en Redis (`llm_budget_service.py`).
   - Cobertura de tests: 103/103 pruebas unitarias pasando en `pytest` al 100%.

---

### 🎯 Tu Misión en esta Tercera Pasada de Certificación Final:
Por favor, realiza la evaluación de cierre sobre el archivo `FULL_PROJECT_ARCHITECTURE_MAP.md` enfocado en:

#### 1. 🏆 Emisión del Production Readiness Score (0 a 100%)
- Evalúa la madurez de la arquitectura global y proporciona el desglose final por áreas (Auth, DB Async, Resiliencia Celery, Grafo LangGraph, Renderizado, SSE, Anti-IDOR, Presupuesto LLM).

#### 2. 🚀 Recomendaciones Operativas para Despliegue en Producción (Kubernetes / Docker Swarm)
- Indica si existe algún paso adicional recomendado para el monitoreo (Prometheus/Grafana), manejo de secretos o configuración en entornos multi-nodo.

#### 3. 🎯 Hoja de Ruta Futura (Siguientes Pasos de Negocio / Scaling)
- Sugiere 2 o 3 características avanzadas para el roadmap futuro una vez desplegada la versión actual en producción.
```
