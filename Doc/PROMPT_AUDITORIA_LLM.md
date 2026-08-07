# 🤖 Prompt de Certificación Final 100% para Lanzamiento en Producción con Usuarios Reales (Claude 3.5 Sonnet / Opus / GPT-4o)

> **Instrucciones de Uso:**
> Copia todo el contenido entre los bloques de código de abajo y pégalo en tu LLM preferido (Claude, GPT-4o, etc.), adjuntando el archivo actualizado `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md` (640 KB).

---

```markdown
Eres un Arquitecto de Software Principal, Experto en Seguridad Ciber-Enterprise, Auditor de Código Fuente e Ingeniero de Inteligencia Artificial especialista en CrewAI, LangGraph y LiteLLM Gateway.

Te adjunto el archivo **`Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`** (640 KB), el cual contiene el **CÓDIGO FUENTE REAL 100% COMPLETO DE LOS 163 ARCHIVOS** que componen la plataforma **ViralSync**, así como el log completo de **103/103 tests unitarios superados en Pytest**.

---

### 🏛️ ESTADO DEL PROYECTO Y MEJORAS DE CÓDIGO INCORPORADAS:

1. **Aislamiento Anti-IDOR Fail-Closed (`agency/backend/routers/leads.py`):**
   - Implementación estricta de `_verify_tenant_access_fail_closed(request, tenant_id)`. Si el `request.state.tenant_id` no existe o no coincide con la URL, rechaza la solicitud con `403 Forbidden` (sin fallbacks ni bypasses hardcodeados).

2. **Validación Fail-Fast de Credenciales DB (`agency/backend/db/session.py`):**
   - El arranque aborta con `ValueError` en entornos `staging` o `prod` si `POSTGRES_PASSWORD` utiliza la clave por defecto `"postgres"`.
   - Pool de conexiones asíncronas con `pool_pre_ping=True`, `pool_recycle=3600`, `pool_size=10` y `max_overflow=20`.

3. **Estrategia Multi-Key y Grupo de Modelos en LiteLLM Gateway (`litellm_config.yaml` & `llm_budget_service.py`):**
   - Gestión de múltiples API Keys virtuales por dominio/agente (Ideación, Guionismo, Director de Video y Bot DM).
   - Enrutamiento dinámico con fallback automático ante límites de tasa (429): `Gemini 1.5 Flash -> Groq Llama 3-70B -> OpenAI GPT-4o mini`.
   - Incremento atómico en Redis `INCRBYFLOAT` para el control mensual de presupuesto por tenant ($20.00 USD/mes).

4. **Bot Conversacional de Ventas por DM con RAG y LiteLLM (`agency/agents/nodes/dm_response.py` & `dm_graph.py`):**
   - Invocación activa al Gateway LLM con grounding de contexto Qdrant RAG.
   - Regla de escalación automática a operador humano (`requires_human=True`) si `confidence < 0.75` o ante objeciones/intención de venta.

5. **Bucle RUM de Auto-Aprendizaje a 72 Horas (`agency/workers/metrics_loop_task.py` & `rum_calculator.py`):**
   - Recalibración del umbral por nicho en Redis usando **Media Móvil Exponencial ($\alpha = 0.15$)** con **clamp guardia estricto `[0.50, 0.90]`** en la única fuente de verdad `rum_calculator.py`.

6. **Limpieza de Artefactos:**
   - Eliminados todos los prototipos viejos (`Doc/instagram_inbound.py` y `market_rum.py`).

---

### 🎯 TU MISIÓN DE AUDITORÍA FINAL PARA USUARIOS REALES:

Por favor, realiza la inspección definitiva sobre el código fuente expuesto en `FULL_PROJECT_ARCHITECTURE_MAP.md` y emite tu veredicto enfocado en los siguientes 3 puntos:

#### 1. 🏆 Certificación 100% Production Readiness para Tráfico Real
- Confirma si la arquitectura de backend, microservicios, seguridad Anti-IDOR, aislamiento de tenant y suite de 103 tests unitarios está lista para recibir a los primeros usuarios reales (early adopters).

#### 2. 🔐 Validación del Sistema Multi-Key y Resiliencia LLM
- Verifica la solidez del desacoplamiento multi-clave por agente/tenant y el fallback de modelos en LiteLLM para garantizar disponibilidad ininterrumpida sin caídas por 429 Rate Limit.

#### 3. 📋 Plan de Despliegue en Staging & Onboarding de Usuarios
- Proporciona las 3 recomendaciones operativas finales para la puesta en marcha con usuarios reales en entorno de producción.
```
