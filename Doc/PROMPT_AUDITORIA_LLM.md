# 🤖 Prompt de Certificación Definitiva 100% para Lanzamiento en Producción (Claude 3.5 Sonnet / Opus / GPT-4o)

> **Instrucciones de Uso:**
> Copia todo el contenido de abajo y pégalo en tu LLM auditor (Claude, GPT-4o, etc.), adjuntando el mapa actualizado `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md` (640 KB).

---

```markdown
Eres un Arquitecto de Software Principal, Experto en Seguridad Ciber-Enterprise y Auditor de Código Fuente de Nivel Tier-1.

Te adjunto el archivo **`Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`** (640 KB), el cual contiene el **CÓDIGO FUENTE REAL 100% COMPLETO DE LOS 163 ARCHIVOS** que componen el proyecto **ViralSync**, así como el log completo de **104/104 tests unitarios superados en Pytest**.

---

### 🏛️ ESTADO DEL PROYECTO Y RESOLUCIÓN TOTAL DE HALLAZGOS DE SEGURIDAD:

1. **Aislamiento de Tenant Anti-IDOR por JWT (`agency/backend/security/auth.py` & `leads.py`):**
   - `TenantContextMiddleware` decodifica y verifica la firma HMAC SHA-256 del token `Authorization: Bearer <token>` (`decode_access_token`). El `tenant_id` se asigna inmutablemente al contexto del request desde el token firmado.
   - `_verify_tenant_access_fail_closed` en `leads.py` rechaza con `403 Forbidden` si la URL intenta solicitar datos de otro tenant.
   - Test dedicado `test_anti_idor_cross_tenant_rejection` agregado a la suite de Pytest (104 tests pasados).

2. **Validación Fail-Fast de Credenciales JWT (`agency/backend/security/auth.py`):**
   - Se inyectó la guardia de seguridad que aborta el arranque del servidor con `ValueError` en entornos `staging` o `prod` si `JWT_SECRET_KEY` mantiene el valor por defecto.

3. **CORS Restrictivo por Entorno (`agency/backend/main.py`):**
   - Se eliminó `allow_origins=["*"]` con `allow_credentials=True`. Ahora restringe orígenes a `ALLOWED_ORIGINS` en entornos `staging`/`prod`.

4. **Conexión de Endpoints a la DB ORM Async (`agency/backend/routers/leads.py`):**
   - `leads.py` ejecuta la consulta ORM asíncrona real `select(Lead).where(Lead.tenant_id == tenant_id)`.

5. **Tracking Activo de Presupuesto LLM USD (`agency/agents/nodes/dm_response.py`):**
   - `generate_grounded_reply` invoca `track_llm_token_usage` tras cada llamada exitosa a LiteLLM Gateway, registrando los tokens utilizados e incrementando atómicamente el consumo mensual en Redis (`INCRBYFLOAT`).

6. **Suite de Tests de Integridad (104/104 Passed):**
   - La suite de `pytest` cubre desde la resiliencia Celery `task_acks_late=True` hasta la prueba de rechazo cruzado Anti-IDOR (403 Forbidden).

---

### 🎯 TU MISIÓN DE RE-AUDITORÍA FINAL:

Revisa el código fuente embebido en `FULL_PROJECT_ARCHITECTURE_MAP.md` y emite tu dictamen final sobre los 3 puntos:

#### 1. 🏆 Verificación de Resolución del Hallazgo Anti-IDOR
- Confirma si la extracción de `tenant_id` desde `decode_access_token` en `TenantContextMiddleware` junto con `_verify_tenant_access_fail_closed` y la prueba `test_anti_idor_cross_tenant_rejection` cierran de forma definitiva el riesgo de IDOR.

#### 2. 🔌 Conexión de Componentes en Runtime (Presupuesto LLM & DB)
- Revisa las conexiones en `dm_response.py` (con `track_llm_token_usage`) y `leads.py` (con `select(Lead)`).

#### 3. 🏁 Certificación Final 100% Ready para Early Adopters
- Otorga la certificación final para el despliegue con usuarios reales en producción.
```
