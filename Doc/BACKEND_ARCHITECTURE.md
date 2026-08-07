# 📄 BACKEND_ARCHITECTURE.md — ViralSync Platform (SaaS Multi-Tenant AI Agency Backend)

## 🎯 Visión General & Filosofía de Diseño
El backend de **ViralSync** es el motor principal de orquestación multi-agente, cómputo asíncrono, captura de webhooks en tiempo real e integración con modelos de lenguaje (LLM). Construido con **Python 3.11+**, **FastAPI**, **LangGraph**, **CrewAI**, **LiteLLM Proxy**, **Celery** y **PostgreSQL**, sigue los principios de **Clean Architecture**, **Domain-Driven Design (DDD)** y **Event-Driven Architecture (EDA)**.

Su propósito fundamental es ejecutar el ciclo completo de una agencia de marketing de contenido sin intervención humana en las tareas operativas, pero garantizando **barreras de seguridad (Checkpoints)** antes de realizar cualquier acción crítica o de costo.

---

## 🛠️ Stack Tecnológico Backend

| Capa | Tecnología | Rol y Justificación |
|---|---|---|
| **Orquestación de Agentes** | **LangGraph** | `StateGraph` multi-tenant. Persistencia de hilos por cliente (`thread_id = tenant_id`) mediante `PostgresSaver`. Manejo nativo de `interrupt_before`. |
| **Ejecución Creativa** | **CrewAI** | Crews especializadas de agentes con rol, meta y trasfondo (`ideation_crew.py`, `scriptwriting_crew.py`). |
| **Gateway de LLMs** | **LiteLLM Proxy** | Enrutamiento por entorno (`dev`, `staging`, `prod`). Pool de proveedores gratuitos (Groq, Gemini, GitHub Models) + UN solo fallback pagado. Virtual keys y presupuesto por tenant. |
| **Protocolo de Herramientas** | **Model Context Protocol (MCP)** | Servidores agnósticos (`searxng_mcp_server.py`, `rag_mcp_server.py`) que exponen herramientas estandarizadas consumibles por cualquier framework. |
| **Servidor de API & Webhooks** | **FastAPI** | REST API asíncrona alta velocidad, captura de webhooks de Meta con validación HMAC y streaming Server-Sent Events (**SSE**). |
| **Cola de Trabajos Asíncronos** | **Redis 7 + Celery** | Procesamiento pesados en segundo plano (renderizado de video, loop de métricas a 72h). `--concurrency=1` en `dev`. |
| **Base de Datos Relacional** | **PostgreSQL 16** | Aislamiento multi-tenant por `tenant_id`. Guarda tenants, mapa de mercado, umbrales RUM, ideas, guiones, videos, campañas, leads y logs de LLM. |
| **Base de Datos Vectorial / RAG** | **Qdrant** | Almacenamiento de embeddings del "cerebro" de marketing (colección `marketing_brain`) y personaje de marca por tenant. |
| **Almacenamiento de Archivos** | **MinIO / AWS S3 / Cloudflare R2** | Almacenamiento persistente de videos crudos subidos por el cliente y videos editados finales. |
| **Procesamiento de Video/Audio** | **MoviePy / FFmpeg / Whisper** | Trimming de silencios muertos, subtitulado quemado de alta legibilidad, inserción de B-roll e interrupciones de patrón SFX. |

---

## 📁 Estructura de Directorios (`/agency`)

```
agency/
├── agents/                     # Capa de Orquestación y Agentes (LangGraph + CrewAI)
│   ├── graph.py                # StateGraph principal, AgencyState, checkpointer y interrupt_before
│   ├── nodes/                  # Nodos ejecutables del grafo
│   │   ├── ideation.py         # Nodo de ideación + Filtro 5/50 + Scoring RUM
│   │   ├── human_approval.py   # Nodos stub para checkpoints humanos (interrupt)
│   │   ├── scriptwriting.py    # Nodo de guionismo (4 bloques + PPP)
│   │   ├── video_edit.py       # Nodo de encolamiento de trabajo de edición en Celery
│   │   ├── publish.py          # Nodo de publicación oficial vía Instagram Graph API
│   │   ├── rum_calculator.py       # Helper de consulta de umbrales RUM dinámicos en DB
│   │   └── __init__.py
│   ├── crews/                  # Crews de CrewAI por dominio
│   │   ├── ideation_crew.py    # Crew de investigación 4 cuadrantes + SearXNG
│   │   └── scriptwriting_crew.py # Crew de guionismo + RAG personaje de marca
│   ├── mcp_servers/            # Servidores agnósticos Model Context Protocol
│   │   ├── searxng_mcp_server.py # MCP Server para búsquedas sanitizadas
│   │   └── rag_mcp_server.py   # MCP Server para consultas vectoriales en Qdrant
│   └── qualifier/
│       └── lead_qualifier.py   # Agente calificador ligero para DMs/comentarios inbound
├── gateway/                    # Configuración del LLM Proxy (LiteLLM)
│   ├── litellm_config.dev.yaml # Configuración local (Ollama exclusivamente)
│   ├── litellm_config.staging.yaml # Pool gratuito (Groq, Gemini Flash)
│   └── litellm_config.production.yaml # Pool gratuito + UN solo fallback pagado
├── backend/                    # Servidor API FastAPI & Realtime
│   ├── main.py                 # Aplicación FastAPI, routers, CORS y endpoints REST
│   ├── webhooks/
│   │   └── instagram_inbound.py # Captura de webhooks de Meta con firma HMAC X-Hub-Signature-256
│   └── realtime/
│       └── sse_manager.py      # Gestor de streaming Server-Sent Events (SSE) para el dashboard
├── workers/                    # Trabajos en segundo plano (Celery Tasks)
│   ├── celery_app.py           # Instancia y configuración de Celery con Redis broker
│   ├── video_edit_task.py      # Post-producción (silencios, subtítulos Whisper, B-roll, SFX)
│   └── metrics_loop_task.py    # Monitoreo a 72h y clasificación Rojo/Amarillo/Verde
├── knowledge/                  # Base de conocimiento del "Cerebro de Marketing"
│   ├── rum_formula.md          # Especificación RUM
│   ├── filter_5_50.md          # Especificación Filtro 5/50
│   ├── ppp_promise.md          # Promesa Principal de Producto
│   ├── script_4_blocks.md      # Estructura de guion 4 bloques
│   ├── brand_character.md      # Personaje de marca RAG
│   ├── pdh_triangle.md         # Evaluación PDH
│   ├── competitor_quadrants.md # Matriz 4 cuadrantes
│   ├── classification_80_20.md # Métricas 72h
│   ├── inbound_funnel.md       # Conversión inbound
│   └── ingest_knowledge.py     # Script de carga de embeddings a Qdrant
├── migrations/                 # Esquema de Base de Datos PostgreSQL
│   └── 001_init_schema.sql     # Tablas multi-tenant (tenants, ideas, scripts, videos, leads, llm_log)
└── docker-compose.yml          # Orquestación de infraestructura local completa
```

---

## 🏛️ Organización de Arquitectura por Capas

```
                     ┌──────────────────────────────────────────┐
                     │          FastAPI HTTP / Webhooks         │
                     └────────────────────┬─────────────────────┘
                                          │
                                          ▼
                     ┌──────────────────────────────────────────┐
                     │       LangGraph StateGraph Engine        │
                     │  (thread_id = tenant_id, interrupt_before)│
                     └───────┬──────────────────────────┬───────┘
                             │                          │
                             ▼                          ▼
               ┌──────────────────────────┐  ┌──────────────────────────┐
               │   CrewAI Creative Crews  │  │   Celery Worker Tasks    │
               │ (Ideación / Guionismo)   │  │ (Edición Video / 72h)    │
               └─────────────┬────────────┘  └─────────────┬────────────┘
                             │                             │
                             ▼                             ▼
               ┌──────────────────────────┐  ┌──────────────────────────┐
               │    MCP Tool Servers      │  │ PostgreSQL 16 / Qdrant   │
               │  (SearXNG / RAG Qdrant)  │  │ (Multi-Tenant Persistence│
               └─────────────┬────────────┘  └──────────────────────────┘
                             │
                             ▼
               ┌──────────────────────────┐
               │   LiteLLM Proxy Gateway  │
               │ (Free Pool + 1 Paid Fall)│
               └──────────────────────────┘
```

### 1. Capa de Orquestación (`agents/graph.py`)
- **Estado Compartido (`AgencyState`):** `TypedDict` que acumula los artefactos del pipeline (mapa de mercado, ideas candidatas, RUM score, guion de 4 bloques, URI de video editado, post ID y estado de aprobaciones).
- **Checkpoints Humanos:** Configurados mediante `interrupt_before=["human_approval_idea", "human_approval_publish", "publish"]`. El grafo se pausa de forma segura en Postgres y espera una petición externa (`POST /tenants/{id}/ideas/approve`) para reanudar el mismo `thread_id`.

### 2. Capa de Herramientas & MCP (`agents/mcp_servers/`)
- Adopta el **Model Context Protocol (MCP)**.
- `searxng_mcp_server.py`: Realiza búsquedas web limpias, eliminando tags HTML y recortando snippets a ~400 caracteres para no contaminar el context window del LLM.
- `rag_mcp_server.py`: Recupera el contexto de tono y personaje de marca del cliente almacenado en Qdrant.

### 3. Capa de Gateway LLM (`gateway/`)
- Enrutamiento transparente a través de `LiteLLM Proxy`. Los agentes consumen `OPENAI_API_BASE=http://localhost:4000/v1`.
- Regla de diseño no negociable: **Pool gratuito como primera línea + UN solo proveedor pagado como fallback final en producción**. En `dev`, utiliza exclusivamente **Ollama local**.

### 4. Capa de API & Inbound (`backend/`)
- Expone los endpoints de administración multi-tenant y desencadena la ejecución del grafo.
- `instagram_inbound.py`: Recibe webhooks de Instagram, valida la firma **HMAC SHA-256 (`X-Hub-Signature-256`)** de Meta y califica el lead de forma liviana asociándolo al `video_id` de origen.
- `sse_manager.py`: Emite eventos Server-Sent Events a la interfaz gráfica en tiempo real.

### 5. Capa Asíncrona & Renderizado (`workers/`)
- **Celery Tasks:** Ejecuta las tareas intensivas fuera del hilo del servidor web.
- `video_edit_task.py`: Limpia silencios muertos con MoviePy, genera subtítulos quemados con Whisper, inserta B-roll e interrupciones de patrón SFX.
- **Regla de Concurrencia en Dev:** Ejecución obligatoria con `--concurrency=1` para evitar saturación de memoria en equipos de desarrollo (16GB RAM / 4 núcleos).

---

## ⚠️ Deuda Técnica & Plan de Mitigación

A medida que el sistema pase del MVP a fase de producción masiva (GA), se deben abordar las siguientes áreas de mejora identificadas:

### 1. Migración a ORM Asíncrono Completo (SQLAlchemy 2.0 / AsyncPG)
- **Estado Actual:** `main.py` contiene diccionarios en memoria (`TENANTS_DB`, `LEADS_DB`) para simplificar pruebas locales rápidas sin base de datos activa.
- **Impacto:** Pérdida de estado de tenants al reiniciar el proceso si no hay Postgres conectado.
- **Plan de Mitigación:** Reemplazar el almacenamiento en memoria por repositorios asíncronos utilizando `SQLAlchemy 2.0` + `asyncpg` conectados directamente a PostgreSQL 16.

### 2. Aceleración por GPU para Whisper & Renderizado de Video
- **Estado Actual:** La tarea `video_edit_task.py` ejecuta Whisper y MoviePy en CPU en serie en entorno `dev`.
- **Impacto:** Tiempo de renderizado de 2 a 5 minutos por Reel en procesadores estándar.
- **Plan de Mitigación:** En entornos `staging` y `production`, desplegar los workers de Celery sobre instancias con GPU NVIDIA (soporte CUDA) o integrar Whisper API de baja latencia.

### 3. Gestión Novedosa de Secretos & Renovación de Tokens de Instagram
- **Estado Actual:** Las credenciales de Instagram Graph API se guardan como referencias simbólicas en la tabla `tenants`.
- **Impacto:** Expiración de tokens de larga duración de Meta a los 60 días sin renovación automática.
- **Plan de Mitigación:** Implementar un worker en segundo plano para refrescar tokens de Instagram cada 45 días e integrar **HashiCorp Vault** o **AWS Secrets Manager** para el almacenamiento cifrado de claves.

### 4. Resiliencia de la Conexión SSE (Server-Sent Events)
- **Estado Actual:** El canal SSE utiliza un generador asíncrono simple en FastAPI.
- **Impacto:** Si la conexión de red del cliente se interrumpe, los eventos emitidos durante la desconexión se pierden.
- **Plan de Mitigación:** Implementar almacenamiento temporal de eventos en Redis con soporte del header `Last-Event-ID` para permitir reconexiones transparentes sin pérdida de mensajes.

### 5. Isolation Sandbox para Automatizaciones con `browser-use`
- **Estado Actual:** `browser-use` está instalado en el mismo entorno que el backend para tareas de investigación interna.
- **Impacto:** Consumo elevado de recursos por Chromium/Playwright dentro del mismo contenedor.
- **Plan de Mitigación:** Aislar la automatización de navegador en un microservicio contenedor independiente expuesto vía gRPC/REST.

---

## 🔒 Reglas de Seguridad & Buenas Prácticas

1. **Validación Obligatoria de HMAC:** Todo webhook recibido en `/webhooks/instagram` **debe** verificar el header `X-Hub-Signature-256` utilizando la clave secreta de la app de Meta. Peticiones no firmadas se descartan con HTTP 401.
2. **Aislamiento Multi-Tenant:** Todas las consultas a PostgreSQL y colecciones de Qdrant deben incluir el filtro explícito `tenant_id = %s`.
3. **Prohibición de Scraping en Instagram:** Está estrictamente prohibido usar `browser-use` o automatizadores de navegador contra la cuenta de Instagram del cliente. Toda interacción oficial se realiza vía **Instagram Graph API**.
4. **Sanitización de Contenido Web:** Cualquier texto recuperado de SearXNG pasa por el wrapper de sanitización antes de enviarse al prompt del LLM.

---

## 🧪 Estrategia de Testing Backend

- **Pruebas Unitarias (`pytest`):** Cobertura de helpers RUM (`rum_calculator.py`), lógica de scoring 5/50 y formateadores de guiones.
- **Pruebas de Integración:** Verificación de endpoints FastAPI, generación de firma HMAC en webhooks y respuestas del proxy LiteLLM.
- **Prueba End-to-End (E2E):** Ejecución del flujo completo en `AGENCY_ENV=dev` contra modelos locales Ollama para validar el StateGraph sin costo.
