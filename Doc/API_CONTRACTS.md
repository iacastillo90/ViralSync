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

### 3.5 `GET /api/v1/tenants/{tenant_id}/leads` (Listar Leads)
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

## 📡 4. Flujo SSE (Server-Sent Events) & Hook `useSSEStream.js`

### 4.1 Endpoint SSE Backend (`GET /realtime/sse/{tenant_id}`)
El backend emite eventos formateados como `text/event-stream`:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Estructura del Evento SSE:**
```
event: node_change
data: {"node":"ideation","status":"running","message":"Investigando tendencias en SearXNG..."}

event: log_entry
data: {"timestamp":"2026-08-06T02:05:00Z","level":"INFO","module":"RUMScorer","message":"RUM Score calculado: 0.444 (PASS)"}

event: checkpoint_paused
data: {"node":"human_approval_idea","status":"paused","message":"Esperando aprobación humana de idea RUM"}
```

---

### 4.2 Integración en Next.js (`useSSEStream.js`)

El hook `useSSEStream.js` se suscribe al canal SSE y actualiza la tienda global de **Zustand** (`useAgentStore`) sin provocar re-renderizados pesados en todo el árbol de React:

```javascript
// agency/frontend/src/hooks/useSSEStream.js
import { useEffect } from "react";
import { useAgentStore } from "@/stores/useAgentStore";

export function useSSEStream(tenantId) {
  const { setNodeState, addLog, setCheckpointPaused } = useAgentStore();

  useEffect(() => {
    if (!tenantId) return;

    const sseUrl = `http://localhost:8000/realtime/sse/${tenantId}`;
    const eventSource = new EventSource(sseUrl);

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
      console.error("Error en conexión SSE:", err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [tenantId, setNodeState, addLog, setCheckpointPaused]);
}
```
