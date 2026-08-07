# 🤖 Prompt Maestro para Auditoría con CÓDIGO FUENTE 100% COMPLETO y Salida Real de Pytest (Claude 3.5 Sonnet / Opus / GPT-4o)

> **Instrucciones de Uso:**
> Copia todo el contenido entre los bloques de código de abajo y pégalo en tu LLM preferido (Claude, GPT-4o, etc.), adjuntando o pegando el archivo completo `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md` (647 KB).

---

```markdown
Eres un Arquitecto de Software Principal, Experto en Seguridad Ciber-Enterprise, Auditor de Código Fuente e Ingeniero de Inteligencia Artificial (CrewAI / LangGraph).

Te adjunto el archivo **`Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`** (647 KB), el cual contiene el **CÓDIGO FUENTE REAL 100% COMPLETO** de los 166 archivos que componen la plataforma **ViralSync** (incluyendo todos los paquetes Python backend, routers FastAPI, agentes CrewAI, microservicios, tareas Celery y la suite completa de pruebas unitarias), así como la **SALIDA REAL Y VERBOSA DE LA EJECUCIÓN DE PYTEST** (`pytest agency/tests/unit/ -v`).

### 🔎 CÓDIGO FUENTE REAL A AUDITAR LÍNEA POR LÍNEA:
Por favor, NO asumas nada por narrativa. Inspecciona directamente las líneas de código fuente embebidas en el archivo adjunto para verificar:

1. **Recalibración EMA RUM y Clamp Guardia (`agency/agents/criterion/rum_calculator.py` y `agency/workers/metrics_loop_task.py`):**
   - Revisa las líneas de código donde se calcula `new_threshold = current_threshold + EMA_ALPHA * (normalized_engagement - current_threshold)` con `EMA_ALPHA = 0.15`.
   - Revisa la función `get_dynamic_threshold(niche)` y confirma la aplicación estricta del clamp `max(0.50, min(0.90, round(threshold, 2)))`.
   - Confirma que `agency/agents/nodes/market_rum.py` fue borrado del árbol y ya no existe como duplicado.

2. **Aislamiento Anti-IDOR en Routers REST (`agency/backend/routers/leads.py`):**
   - Inspecciona los endpoints `@router.get("/{tenant_id}/leads")` y `@router.post("/{tenant_id}/leads/{lead_id}/takeover")`.
   - Verifica la comprobación explicita `if req_tenant != tenant_id ... raise HTTPException(status_code=403)` para prevenir el bypass de tenants.

3. **Robustecimiento del Pool Asíncrono de Base de Datos (`agency/backend/db/session.py`):**
   - Inspecciona la función `create_async_engine(TARGET_DB_URL, **engine_kwargs)` y confirma la presencia de `pool_pre_ping=True`, `pool_recycle=3600`, `pool_size=10` y `max_overflow=20`.

4. **Resiliencia Celery (`agency/workers/celery_app.py`):**
   - Inspecciona `celery_app.conf.update(...)` y confirma `task_acks_late=True` y `task_reject_on_worker_lost=True`.

5. **Bot Conversacional de Ventas por DM con RAG (`agency/agents/dm_graph.py` y `agency/agents/nodes/dm_response.py`):**
   - Inspecciona la implementación del `StateGraph` de LangGraph, la función `classify_intent` y la regla de escalación a humano si `confidence < 0.75` o si `intent` pertenece a `objection` o `purchase_intent`.

6. **Verificación de Pruebas Unitarias Reales (Sección Pytest Output):**
   - Revisa la sección `## 🧪 Salida Real de Ejecución de Pytest` y confirma el paso de los 103 tests unitarios, incluyendo `test_audit_second_pass_resolutions.py`.

---

### 🎯 Tu Misión:
Habiendo leído el CÓDIGO FUENTE REAL y la SALIDA REAL DE PYTEST contenidos en el documento:

1. **Emisión de Veredicto Definitivo:** Emite el análisis de auditoría técnica basado 100% en la inspección directa del código fuente expuesto.
2. **Recomendaciones para Producción:** Aporta las observaciones finales para el despliegue multi-nodo en staging y producción.
```
