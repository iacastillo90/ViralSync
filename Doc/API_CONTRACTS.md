# 📄 API_CONTRACTS.md — ViralSync Platform (REST, SSE & Payload Schemas)

## 🎯 Visión General
Este documento define los **contratos API oficiales**, la especificación exacta de payloads JSON y la mecánica de comunicación en tiempo real mediante **Server-Sent Events (SSE)** entre el backend FastAPI (`/agency/backend`) y el frontend Next.js (`/agency/frontend`).

---

## 🌐 1. Convenciones REST & Versionamiento
- **Base URL API:** `http://localhost:8000/api/v1`
- **Base URL Webhooks:** `http://localhost:8000/webhooks`
- **Base URL SSE Realtime:** `http://localhost:8000/realtime/sse/{tenant_id}`
- **Cabeceras Obligatorias:**
  - `Content-Type: application/json`
  - `X-Tenant-ID: <uuid-o-tenant-slug>`

---

## 🗺️ 2. Rutas REST Principales

| Método | Ruta | Descripción | Checkpoint Asociado |
|---|---|---|---|
| `POST` | `/api/v1/tenants` | Onboarding de nuevo tenant | — |
| `GET` | `/api/v1/tenants/{tenant_id}` | Obtener configuración y estado actual del tenant | — |
| `POST` | `/api/v1/tenants/{tenant_id}/graph/run` | Iniciar o reanudar ejecución del StateGraph | — |
| `POST` | `/api/v1/tenants/{tenant_id}/ideas/approve` | Aprobar o rechazar idea candidata RUM | `human_approval_idea` |
| `POST` | `/api/v1/tenants/{tenant_id}/publish/approve` | Aprobar o rechazar publicación del video editado | `human_approval_publish` |
| `GET` | `/api/v1/tenants/{tenant_id}/leads` | Listar leads calificados con atribución a video | — |
| `POST` | `/api/v1/tenants/{tenant_id}/leads/{lead_id}/takeover` | Marcar lead como tomado por operador humano | — |
| `GET` | `/api/v1/tenants/{tenant_id}/metrics` | Obtener clasificación 80/20 post-publicación (72h) | — |
| `POST` | `/webhooks/instagram` | Receptor de webhooks Meta (DMs y comentarios) | — |

---

## 📦 3. Esquemas JSON Exactos (Request & Response)

### 3.1 `POST /api/v1/tenants` (Crear Tenant)
**Request Payload:**
```json
{
  "name": "Cliente Demo Marketing",
  "niche": "Negocios B2B y SaaS",
  "monthly_llm_budget_usd": 20.00
}
```

**Response 201 Created:**
```json
{
  "id": "tenant-demo-001",
  "name": "Cliente Demo Marketing",
  "niche": "Negocios B2B y SaaS",
  "litellm_virtual_key": "sk-agency-tenant-demo-001",
  "monthly_llm_budget_usd": 20.00,
  "created_at": "2026-08-06T00:00:00Z"
}
```

---

### 3.2 `POST /api/v1/tenants/{tenant_id}/graph/run` (Ejecutar Grafo)
**Request Payload:**
```json
{
  "force_reideation": false
}
```

**Response 200 OK:**
```json
{
  "tenant_id": "tenant-demo-001",
  "thread_id": "tenant-demo-001",
  "status": "running",
  "current_node": "ideation",
  "message": "Grafo LangGraph iniciado desde el nodo ideation."
}
```

---

### 3.3 `POST /api/v1/tenants/{tenant_id}/ideas/approve` (Checkpoint Idea RUM)
**Request Payload:**
```json
{
  "idea_id": "idea-101",
  "status": "approved"
}
```

**Response 200 OK:**
```json
{
  "tenant_id": "tenant-demo-001",
  "idea_id": "idea-101",
  "idea_approval_status": "approved",
  "next_node": "scriptwriting",
  "state_summary": {
    "rum_score": 0.444,
    "rum_threshold": 0.050,
    "passes_5_50": true
  }
}
```

---

### 3.4 `POST /api/v1/tenants/{tenant_id}/publish/approve` (Checkpoint Publicación Video)
**Request Payload:**
```json
{
  "status": "approved"
}
```

**Response 200 OK:**
```json
{
  "tenant_id": "tenant-demo-001",
  "publish_approval_status": "approved",
  "published_post_id": "ig_reel_8839102",
  "next_node": "publish",
  "published_at": "2026-08-06T02:00:00Z"
}
```

---

### 3.5 `GET /api/v1/tenants/{tenant_id}/leads` (Listar Leads Calificados)
**Response 200 OK:**
```json
[
  {
    "id": "lead-001",
    "tenant_id": "tenant-demo-001",
    "video_id": "video-55",
    "keyword": "CONSULTA",
    "ig_user_id": "user_ig_9921",
    "mensaje_original": "Hola! Quiero la CONSULTA por favor",
    "origen": "comment",
    "calificado_at": "2026-08-06T01:45:00Z",
    "handled_by_human_at": null,
    "outcome": null
  }
]
```

---

### 3.6 `POST /api/v1/tenants/{tenant_id}/leads/{lead_id}/takeover` (Toma de Control Humano)
**Descripción:** El Account Manager o el cliente asume la conversación en Instagram desde el dashboard. El bot calificador deja de enviar respuestas automáticas a este usuario.

**Request Payload:**
```json
{
  "operator_id": "admin_uuid_443",
  "action": "pause_bot"
}
```

**Response 200 OK:**
```json
{
  "lead_id": "lead-001",
  "status": "handled_by_human",
  "handled_by_human_at": "2026-08-06T02:30:00Z",
  "message": "Bot pausado. Operador asignado exitosamente."
}
```

---

### 3.7 `GET /api/v1/tenants/{tenant_id}/metrics` (Clasificación 80/20 a las 72h)
**Descripción:** Obtiene el listado de videos publicados clasificados mediante el ratio de vistas/seguidores a las 72h (Rojo, Amarillo, Verde).

**Response 200 OK:**
```json
[
  {
    "video_id": "video-55",
    "published_at": "2026-08-03T10:00:00Z",
    "metrics_72h": {
      "views": 150000,
      "followers_at_posting": 10000,
      "ratio": 15.0,
      "leads_generated": 142
    },
    "classification": "VERDE",
    "action_taken": "Encolado para 3 variaciones en próximo batch."
  },
  {
    "video_id": "video-56",
    "published_at": "2026-08-03T14:00:00Z",
    "metrics_72h": {
      "views": 4500,
      "followers_at_posting": 10000,
      "ratio": 0.45,
      "leads_generated": 2
    },
    "classification": "ROJO",
    "action_taken": "Idea descartada."
  }
]
```

---

## 📡 4. Flujo SSE (Server-Sent Events) & Hook `useSSEStream.js`

### 4.1 Endpoint SSE Backend (`GET /realtime/sse/{tenant_id}`)
El backend emite eventos formateados como `text/event-stream`:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Estructura de Eventos SSE:**
```
event: node_change
data: {"node":"ideation","status":"running","message":"Investigando tendencias en SearXNG..."}

event: log_entry
data: {"timestamp":"2026-08-06T02:05:00Z","level":"INFO","module":"RUMScorer","message":"RUM Score calculado: 0.444 (PASS)"}

event: checkpoint_paused
data: {"node":"human_approval_idea","status":"paused","message":"Esperando aprobación humana de idea RUM"}
```

---

### 4.2 Integración en Next.js (`useSSEStream.js`) con Reconexión Resiliente

Para blindar la conexión contra parpadeos de red en producción, el custom hook implementa **reconexión automática con retry exponencial** y re-suscripción limpia a la tienda de **Zustand** (`useAgentStore`):

```javascript
// agency/frontend/src/hooks/useSSEStream.js
import { useEffect, useRef } from "react";
import { useAgentStore } from "@/stores/useAgentStore";

export function useSSEStream(tenantId) {
  const { setNodeState, addLog, setCheckpointPaused } = useAgentStore();
  const retryCountRef = useRef(0);
  const maxRetries = 5;

  useEffect(() => {
    if (!tenantId) return;

    let eventSource = null;
    let timeoutId = null;

    const connectSSE = () => {
      const sseUrl = `http://localhost:8000/realtime/sse/${tenantId}`;
      eventSource = new EventSource(sseUrl);

      eventSource.onopen = () => {
        retryCountRef.current = 0; // Resetear intentos en éxito
      };

      eventSource.addEventListener("node_change", (e) => {
        const data = JSON.parse(e.data);
        setNodeState(data.node, data.status);
      });

      eventSource.addEventListener("log_entry", (e) => {
        const data = JSON.parse(e.data);
        addLog(`[${data.module}] ${data.message}`);
      });

      eventSource.addEventListener("checkpoint_paused", (e) => {
        const data = JSON.parse(e.data);
        setCheckpointPaused(data.node, true);
      });

      eventSource.onerror = (err) => {
        console.warn("Parpadeo de red en SSE. Reconectando...", err);
        eventSource.close();

        if (retryCountRef.current < maxRetries) {
          const timeout = Math.pow(2, retryCountRef.current) * 1000; // Exponential backoff (1s, 2s, 4s, 8s...)
          retryCountRef.current += 1;
          timeoutId = setTimeout(connectSSE, timeout);
        } else {
          console.error("Límite de reconexiones SSE alcanzado.");
        }
      };
    };

    connectSSE();

    return () => {
      if (eventSource) eventSource.close();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [tenantId, setNodeState, addLog, setCheckpointPaused]);
}
```
