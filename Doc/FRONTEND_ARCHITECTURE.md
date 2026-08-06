# 📄 FRONTEND_ARCHITECTURE.md — ViralSync Platform (SaaS Multi-Tenant AI Agency)

## 🎯 Visión General & Filosofía de Diseño
ViralSync es un **SaaS multi-tenant** que automatiza el ciclo completo de agencias de contenido con inteligencia artificial. No es un wrapper genérico de LLM: codificamos estrategias probadas de marketing (**fórmula RUM**, **filtro 5/50**, **promesa PPP**, **guion de 4 bloques** y **clasificación 80/20**) en un flujo orquestado por agentes autónomos con **LangGraph**, **CrewAI** y **LiteLLM Gateway**.

La arquitectura del frontend adopta los principios de **Domain-Driven Design (DDD)** y un enfoque **Feature-First** para **Next.js 14 (App Router) + React 18 + Tailwind CSS**. Ofrece una interfaz premium con estética moderna (glassmorphism, modo oscuro nativo, micro-animaciones HSL y consumo en tiempo real mediante **Server-Sent Events - SSE** con gestor de estado ultra-liviano **Zustand**).

---

## 🏗️ Estructura de Directorios (`/agency/frontend/src`)

```
agency/frontend/src/
├── middleware.js               # Guardián de enrutamiento Multi-Tenant en servidor (Seguridad JWT & URL Isolation)
├── app/                        # Next.js App Router (Rutas y Puntos de Entrada)
│   ├── layout.js               # Layout raíz (Proveedores de contexto, HTML base, CSS global)
│   ├── page.js                 # Dashboard Principal unificado (Tabs & Vistas)
│   ├── globals.css             # Design System tokens, glassmorphism utilities y animación
│   └── (routes)/               # Rutas parametrizadas por tenant
│       └── tenants/
│           └── [tenantId]/
│               ├── page.js     # Vista detallada de un tenant
│               └── leads/
│                   └── page.js # Vista de atribución de leads
├── components/                 # Design System (Basado en Primitivas Headless Radix UI / shadcn)
│   ├── ui/                     # Componentes Atómicos con Tailwind Glassmorphism
│   │   ├── Button/             # Botones de acción (Primary, Danger, Glass)
│   │   ├── Card/               # Contenedores Glassmorphism
│   │   ├── Badge/              # Badges de estado (Rojo/Amarillo/Verde/Pending)
│   │   ├── Dialog/             # Modales accesibles (Radix UI Primitive)
│   │   ├── Tabs/               # Pestañas desacopladas
│   │   └── ProgressBar/        # Barras de medición RUM y presupuesto LLM
│   └── layout/
│       ├── Header.jsx          # Barra superior con selector de tenant y presupuesto LLM
│       └── Sidebar.jsx         # Navegación principal por módulos DDD
├── stores/                     # Estado Global Ultraligero (Zustand - Sin re-renders en cascada)
│   ├── useAgentStore.js        # Estado del grafo LangGraph, streaming SSE y logs en vivo
│   └── useTenantStore.js       # Tenant activo, Virtual Keys y límites presupuestarios LLM
├── hooks/                      # Custom Hooks Universales / Utilitarios
│   ├── useSSEStream.js         # Suscripción al endpoint SSE /realtime/sse/{tenant_id}
│   ├── useTenantBudget.js      # Monitoreo en tiempo real del consumo de LiteLLM
│   └── useMediaQuery.js        # Responsive breakpoints
├── features/                   # Módulos de Dominio (DDD) / Feature-First
│   ├── Pipeline/               # Orquestación del Grafo LangGraph
│   │   ├── components/         # NodeStepMap, GraphProgressDiagram, SSELogConsole
│   │   ├── hooks/              # useGraphRunner, useNodeState
│   │   ├── services/           # pipelineService.js (POST /tenants/{id}/run)
│   │   └── views/              # PipelineMonitorView.jsx
│   ├── Ideation/               # Módulo de Ideación & Scoring RUM
│   │   ├── components/         # IdeaCard, RUMBreakdownBarChart, Filter550Badge
│   │   ├── hooks/              # useIdeationScorer, useRUMThreshold
│   │   ├── services/           # ideationService.js (POST /tenants/{id}/ideas/approve)
│   │   └── views/              # IdeaApprovalView.jsx
│   ├── Scriptwriting/          # Generación de Guiones en 4 Bloques
│   │   ├── components/         # Script4BlockReader, CTAKeywordBadge, BrandVoiceInspector
│   │   └── views/              # ScriptInspectorView.jsx
│   ├── VideoPreview/           # Edición Asíncrona & Aprobación de Publicación
│   │   ├── components/         # VideoPlayer, WhisperSubtitleOverlay, PatternInterruptList
│   │   ├── services/           # publishService.js (POST /tenants/{id}/publish/approve)
│   │   └── views/              # PublishApprovalView.jsx
│   ├── LeadsInbound/           # Captura Inbound de Webhooks Meta
│   │   ├── components/         # LeadsTable, LeadAttributionCard, HumanTakeoverModal
│   │   ├── services/           # leadsService.js (GET /api/tenants/{id}/leads)
│   │   └── views/              # InboundLeadsView.jsx
│   ├── Metrics72h/             # Clasificación 80/20 (Rojo / Amarillo / Verde)
│   │   ├── components/         # MetricClassificationCard, FollowerRatioChart
│   │   └── views/              # MetricsDashboardView.jsx
│   ├── RAGBrain/               # Cerebro de Marketing & Qdrant Knowledge
│   │   ├── components/         # BrandPersonaEditor, NicheMarketMapInspector
│   │   └── views/              # BrainManagementView.jsx
│   └── index.js                # Public API de exportación limpia para el Router
├── services/                   # Clientes HTTP compartidos (FastAPI Base Client & Interceptores)
│   └── apiConfig.js            # Instancia Fetch/Axios con cabeceras multi-tenant
└── utils/                      # Utilidades globales (Formateadores RUM, conversores USD/CLP)
    ├── rumCalculator.js
    └── formatters.js
```

---

## 📐 Principios de Arquitectura para el Agente / Desarrollador

### 1. `features/` (Bounded Contexts - DDD)
Cada carpeta dentro de `features/` representa un **Dominio de Negocio** exclusivo del pipeline de marketing automatizado (`Pipeline`, `Ideation`, `Scriptwriting`, `VideoPreview`, `LeadsInbound`, `Metrics72h`, `RAGBrain`).

- **Encapsulamiento Estricto:** Los componentes de interfaz, hooks de estado y llamadas API de un dominio viven dentro de su subcarpeta en `features/`.
- **Public API Pattern (`features/index.js`):** Cada módulo expone únicamente sus vistas principales (`Views`) o componentes exportables. La lógica interna permanece privada.

### 2. Estado Global Reactivo con Zustand (`stores/`)
- **Evitar Re-renders en Cascada:** Se reemplaza Context API tradicional por **Zustand** (`useAgentStore.js`, `useTenantStore.js`).
- Como los eventos SSE emiten logs a alta frecuencia mientras los agentes trabajan, Zustand permite que solo el componente `SSELogConsole` o `NodeStepMap` se vuelva a renderizar ante un log entrante, manteniendo el resto del dashboard a 60 FPS estables.

### 3. Seguridad Multi-Tenant en Servidor (`middleware.js`)
- **Seguridad en la Frontera:** El middleware de Next.js intercepta cada solicitud entrante a `/tenants/[tenantId]`.
- Lee la cookie o token de sesión del operador y valida en el servidor que la sesión pertenezca al `tenantId` solicitado antes de renderizar la página. Bloquea de inmediato manipulaciones de URL dirigidas a ver datos de otras marcas.

### 4. Primitivas Headless & Design System (`components/ui/`)
- **Ahorro de Tiempo con Radix UI / shadcn:** Los componentes base interactivas (modales, diálogos de confirmación, menús desplegables, tablas accesibles) utilizan las primitivas sin estilo de Radix UI.
- Sobre estas primitivas se inyectan las clases del Design System de ViralSync (`glass-panel`, bordes neón HSL, micro-animaciones HSL).

---

## 🛠️ Reglas de Código y Patrones Estándar

1. **Uso de Modos de Checkpoint (`interrupt_before`):**
   - El frontend escucha los eventos de pausa en `human_approval_idea` y `human_approval_publish`.
   - Cuando el grafo entra en estado `paused`, el frontend resalta las pestañas de aprobación correspondientes y muestra las acciones de aprobación/rechazo.
2. **Nombres de Archivos:**
   - `PascalCase` para componentes JSX (`IdeaCard.jsx`, `Header.jsx`).
   - `camelCase` para hooks y utilidades (`useSSEStream.js`, `formatRUMScore.js`).
3. **Manejo Multi-Tenant Estricto:**
   - Toda solicitud HTTP enviada al backend incluye el parámetro `tenant_id` o el header `X-Tenant-ID`.
4. **Optimización de Hardware Local (4 Núcleos / 16GB RAM):**
   - La arquitectura SSE unidireccional desacopla el cliente del servidor. El frontend no realiza polling.
   - Combinado con la ejecución serializada de los workers Celery (`--concurrency=1`), el consumo del procesador se mantiene bajo mínimos.

---

## 🧪 Estrategia de Testing

- **Colocación:** Las pruebas unitarias se ubican junto a sus respectivos archivos (`IdeaCard.test.jsx`, `useAgentStore.test.js`).
- **Herramientas:** React Testing Library + Vitest.

---

## 🗺️ Catálogo Completo de Vistas y Rutas Frontend (40 Rutas / 7 Módulos)

El frontend de **ViralSync** cuenta con **40 vistas/sub-módulos organizados en 7 áreas funcionales**, coordinados con el backend de FastAPI, Celery, PostgreSQL, Qdrant y LiteLLM.

### 1. Autenticación, Tenants & Onboarding (5 Módulos)
- **Login / Autenticación de Operador:** `/login`
- **Gestión Multi-Tenant / Selector de Clientes:** `/tenants`
- **Onboarding de Nuevo Cliente:** `/tenants/nuevo` (Definición de nicho, presupuesto mensual en USD y clave virtual de LiteLLM)
- **Configuración de Presupuesto LLM:** `/tenants/:tenantId/presupuesto` (Monitoreo de gasto en tiempo real, alertas de consumo)
- **Perfil de Operador / Credenciales de Agencia:** `/perfil`

### 2. Orquestador de Grafo & Pipeline Monitor (`/tenants/:tenantId/pipeline`) (5 Módulos)
- **Diagrama de Pasos del StateGraph:** Visor visual interactivo del recorrido de nodos en LangGraph (`ideation` ➔ `human_approval_idea` ➔ `scriptwriting` ➔ `video_edit` ➔ `human_approval_publish` ➔ `publish`).
- **Consola de Eventos SSE en Tiempo Real:** Monitor de logs streaming alimentado por `useAgentStore` y `sse_manager.py`.
- **Disparador Manual del Grafo:** Botón de inicio de hilo de ejecución (`POST /tenants/{id}/run`).
- **Historial de Ejecuciones del Grafo:** Registro de ejecuciones anteriores por `thread_id`.
- **Inspector de Errores y Excepciones:** Panel de diagnóstico ante caídas de proveedores o límites de API.

### 3. Checkpoints de Aprobación Humana (`/tenants/:tenantId/aprobaciones`) (6 Módulos)
- **Punto de Control: Evaluación de Ideas (RUM):** `/aprobaciones/ideas` (Revisión de ideas sobrevivientes al Filtro 5/50).
- **Desglose Gráfico de Variables RUM:** Gráficos de barras con puntuaciones de Universalidad, Intensidad, Claridad, Shareability, Distribución y Alineación vs Umbral del Nicho.
- **Acción de Aprobación / Rechazo de Idea:** Disparador para reanudar el grafo o forzar un nuevo batch de ideación (`POST /tenants/{id}/ideas/approve`).
- **Punto de Control: Aprobación de Publicación:** `/aprobaciones/publicacion` (Revisión del video final editado y subtitulado).
- **Visor de Guion en 4 Bloques:** Visualizador estructurado (`gancho_0_5s`, `contexto_5_30s`, `moraleja_30_50s`, `cta_50_60s`).
- **Reproductor de Video Editado:** Preview del renderizado asíncrono con subtítulos Whisper quemados y efectos SFX.

### 4. Captura Inbound de Leads & Conversion Funnel (`/tenants/:tenantId/leads`) (6 Módulos)
- **Tabla de Leads Calificados en Tiempo Real:** `/leads` (Captura desde webhooks de Meta `instagram_inbound.py`).
- **Tarjeta de Atribución Completa por Lead:** Identificación del `video_id` de origen, palabra clave del CTA y timestamp.
- **Modal de Toma de Control Humano:** Botón de transición `Pausar Bot / Tomar Conversación` para que el agente humano cierre la venta.
- **Buscador y Filtro de Leads por Palabra Clave:** Filtrado por campañas activas (ej: "CONSULTA", "GUIA").
- **Filtro de Origen (DM vs Comentario):** Clasificación según canal de entrada en Instagram.
- **Exportador de Leads Calificados (Excel/CSV):** Botón de exportación para integración con CRM.

### 5. Métricas 72h & Clasificación 80/20 (`/tenants/:tenantId/metricas`) (5 Módulos)
- **Dashboard de Clasificación 80/20:** Visor general de rendimiento post-publicación a las 72 horas.
- **Tarjeta de Desempeño Rojo (`< 1.0x`):** Identificación de videos con vistas por debajo de los seguidores (descarte definitivo de idea).
- **Tarjeta de Desempeño Amarillo (`1.0x - 10x`):** Videos de rendimiento moderado programados para reintento en 1-2 formatos nuevos.
- **Tarjeta de Desempeño Verde (`> 10x`):** Videos virales de alto impacto seleccionados para multiplicación de formato.
- **Monitor de Realimentación Automática:** Indicador de ideas re-inyectadas al batch de ideación del mes subsiguiente.

### 6. Cerebro RAG & Configuración de Marca (`/tenants/:tenantId/cerebro`) (6 Módulos)
- **Editor de Personaje de Marca (Brand Persona):** Configuración de los 3 atributos de tono, elementos visuales recurrentes u objeto de identidad.
- **Inspector de Mapa de Mercado:** Consulta de errores, deseos, objeciones y creencias falsas del nicho persistidas en Postgres.
- **Indexador RAG Qdrant:** Estado de sincronización de la colección `marketing_brain`.
- **Configurador de Matriz de Competencia:** Búsqueda en 4 cuadrantes (en-nicho/fuera-nicho x en-plataforma/fuera-plataforma).
- **Evaluador de Triángulo PDH:** Medición de Pasión, Dinero y Habilidad en el onboarding del cliente.
- **Gestor de Palabras Clave de Campaña:** Registro de palabras clave activas e históricas por tenant.

### 7. Infraestructura, LLM Gateway & Consumos (`/admin/sistema`) (7 Módulos)
- **Panel LiteLLM Proxy Gateway:** Estado en vivo del pool gratuito (Groq, Gemini, GitHub Models, Cerebras, SambaNova) y fallback pagado en producción.
- **Monitor de Tareas Celery:** Estado de la cola Redis y tareas de edición de video en serie (`--concurrency=1` en dev).
- **Monitor de Conexión SearXNG:** Estado del motor de búsqueda web sanitizada.
- **Monitor de Salud Qdrant Vector Database:** Memoria y colecciones indexadas.
- **Consola de Logs de Backend FastAPI:** Visor estilo terminal para depurar webhooks y ejecuciones de LangGraph.
- **Gestor de Tokens e Integraciones Meta:** Estado de tokens de acceso a Instagram Graph API por tenant.
- **Visor de Auditoría de Consumo LLM:** Desglose de tokens de entrada/salida y costo en USD por nodo ejecutado.
