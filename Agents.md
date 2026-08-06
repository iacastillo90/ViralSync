# AGENTS.md — Agencia de Marketing Multiagente

Este archivo es la fuente de verdad para cualquier agente (Claude Code, Cursor, Codex, o un humano nuevo en el equipo) que trabaje en este repositorio. Antes de tocar código, léelo completo — especialmente la sección 7 (conocimiento de dominio), porque de ahí sale la lógica de negocio que este software automatiza.

---

## 1. Qué es este proyecto

Un sistema multiagente que automatiza el ciclo completo de una agencia de contenido para redes sociales — desde la investigación de nicho hasta la publicación y el análisis de métricas — para múltiples clientes (tenants). No reemplaza al humano en las decisiones de negocio ni en la grabación del video; automatiza la investigación, la generación de ideas evaluadas con un criterio objetivo, el guion, la postproducción y el ciclo de aprendizaje sobre qué funciona.

El flujo completo, por tenant:

```
Ingesta de nicho (una vez)
   → Mapa de mercado (errores / deseos / objeciones / creencias falsas)
   → Generación de ideas (agente + búsqueda web real)
   → Scoring RUM + filtro 5/50 (descarta lo que no pasa el umbral)
   → ⏸ CHECKPOINT HUMANO — aprobar idea
   → Generación de guion (JSON de 4 bloques)
   → Producción de video (el humano graba; el sistema edita: silencios, subtítulos, B-roll, SFX)
   → ⏸ CHECKPOINT HUMANO — aprobar publicación
   → Publicación vía Instagram Graph API (oficial, nunca automatización de navegador)
   → Loop de métricas a 72h → clasificación Rojo/Amarillo/Verde
   → Alimenta la ideación del mes siguiente (lo que funcionó se reintenta en otros formatos)
```

Es un **producto SaaS multi-tenant**: cada cliente tiene su propio namespace de datos, su propio presupuesto de LLM y su propio historial de contenido.

---

## 2. Principio rector: FREE primero, un solo PAID en producción

Regla de diseño no negociable de este proyecto:

- **Desarrollo local:** modelos locales vía Ollama. Cero costo, cero riesgo de cuota, iteración rápida sobre la lógica del grafo sin gastar nada.
- **Staging / pruebas de integración:** pool de proveedores gratuitos reales (ver tabla abajo) a través de LiteLLM, para validar comportamiento real de API, límites de tasa y fallbacks — pero **nunca** el proveedor pagado en esta fase.
- **Producción:** el mismo pool gratuito como primera línea, con **exactamente un** proveedor pagado como fallback final. No apilar varios proveedores pagados — la razón es simplicidad de facturación y de superficie de fallo, no solo costo.

Esto se controla con la variable de entorno `AGENCY_ENV` (`dev` / `staging` / `production`) y el router de LiteLLM lee un `config.yaml` distinto según el entorno (ver sección 9).

**Por qué esto importa y no es solo tacañería:** los tiers gratuitos de la mayoría de estos proveedores prohíben o restringen el uso comercial en sus términos de servicio. Este pool gratuito es para *desarrollo y pruebas*, y en producción sigue usándose para las tareas de menor criticidad — pero el fallback pagado único es lo que garantiza que un cliente que paga no se quede sin servicio si un proveedor gratuito cambia sus condiciones de un día para otro. No crear múltiples cuentas por proveedor para multiplicar cuota — es la práctica que más rápido puede tumbar todo el sistema en producción.

### Pool de proveedores gratuitos (capa dev/staging + tareas no críticas en prod)

| Proveedor | Modelo | Rol en el pipeline |
|---|---|---|
| Google AI Studio | Gemini 2.5 Flash | Análisis de entrada larga (transcripciones, mapa de mercado) |
| Groq | Llama 3.3 70B | Generación de ideas, guiones JSON, baja latencia |
| GitHub Models | GPT-4o / Llama 3.3 | Validación y refinamiento (filtro 5/50, segunda opinión) |
| Cerebras | Llama 3.1 | Extracción de keywords para B-roll |
| SambaNova | Llama 3.1 405B | Variaciones creativas de ganchos |
| OpenRouter (free) | Varios | Router de respaldo dentro del propio pool |
| Ollama local | qwen2.5-coder / llama3.2 | Respaldo final infalible, y única opción en `dev` |

### Fallback pagado único (producción)

Elige **uno** y documenta la elección aquí cuando se decida — no lo dejes ambiguo en el código:

- Claude Haiku (buena relación costo/calidad para tareas de generación de guion/scoring)
- Gemini Flash (tier pagado, si ya se usa su tier gratis en el pool y se quiere consistencia de proveedor)
- GPT-4o-mini / GPT-5-mini (si el resto del stack ya vive en el ecosistema OpenAI)

---

## 3. Stack tecnológico

| Capa | Tecnología | Rol |
|---|---|---|
| Orquestación | **LangGraph** | Grafo de estado, checkpoints humanos, persistencia de ejecución |
| Ejecución creativa | **CrewAI** | Crews de agentes con rol (estratega, guionista, editor) dentro de cada nodo del grafo |
| Gateway de LLMs | **LiteLLM Proxy** | Pool free-tier + fallback pagado único, virtual keys por tenant |
| Búsqueda web | **SearXNG** + wrapper de sanitización propio | Alimentación de internet gratis, sin API keys de terceros |
| Memoria / RAG | **Qdrant** + **LlamaIndex** | Brand voice por cliente, guiones que ya funcionaron, mapa de mercado persistente |
| Estandarización de tools | **MCP (Model Context Protocol)** | Expone `searxng_tool` y `rag_tool` como servidores agnósticos al framework — no atados solo a CrewAI |
| Automatización de navegador | **browser-use** | Solo tareas internas (investigación en sitios sin API) — nunca contra Instagram |
| Publicación real | **Instagram Graph API** (oficial) | Único canal permitido para publicar/interactuar con la cuenta del cliente |
| Captura inbound | **Instagram Graph API Webhooks** | Escucha DMs/comentarios con palabra clave en tiempo real — el motor de conversión (ver 7.9) |
| Cola de trabajos | Redis + Celery | Render de video, jobs largos, desacopla del backend síncrono |
| Procesamiento de video | Python: moviepy / ffmpeg / Whisper | Limpieza de silencios, subtítulos, SFX, B-roll |
| Backend | FastAPI (Python) | API, auth, tenants, orquesta invocaciones al grafo |
| Comunicación en tiempo real | FastAPI **SSE** (o WebSocket si se necesita bidireccional) | Transmite al dashboard en qué nodo del grafo está cada ejecución, evita timeouts de REST en tareas largas |
| Frontend | Next.js | Dashboard multi-tenant, botón de aprobación humana |
| Base de datos | PostgreSQL | Tenants, ideas, guiones, métricas |
| Storage | S3 / R2 | Video crudo y final |

---

## 4. Repos y dependencias — instalación

No todo esto es "clonar un repo": la mayoría son paquetes. Se listan con el método correcto de cada uno.

```bash
# Orquestación (pip)
pip install langgraph langgraph-checkpoint-postgres
pip install crewai crewai-tools

# Gateway LLM (pip, se corre como proxy local)
pip install 'litellm[proxy]'
# alternativa con panel visual (Go, opcional, solo si quieres GUI de administración):
# git clone https://github.com/new-api/new-api  # verificar org/fork activo antes de clonar

# Búsqueda (docker — NO se instala por pip)
docker pull searxng/searxng
# o clonar para configuración avanzada:
# git clone https://github.com/searxng/searxng

# Memoria / RAG
docker pull qdrant/qdrant
pip install llama-index llama-index-vector-stores-qdrant

# Automatización de navegador (solo uso interno)
pip install browser-use
playwright install chromium

# Backend / cola
pip install fastapi celery redis[hiredis] sqlalchemy psycopg2-binary

# Video
pip install moviepy openai-whisper
# ffmpeg se instala a nivel de sistema, no vía pip
```

---

## 5. Estructura de carpetas

```
/agency
  /agents
    /nodes           # cada nodo del grafo LangGraph vive aquí
      ideation.py
      human_approval.py
      scriptwriting.py
      video_edit.py
      publish.py
    /crews            # definiciones de Agent/Task/Crew de CrewAI, agrupadas por nodo
      ideation_crew.py
      scriptwriting_crew.py
    /tools             # legacy: @tool embebidos — migrar a /mcp_servers cuando se consuman desde más de un framework
      searxng_tool.py
      rag_tool.py
    /mcp_servers         # herramientas expuestas vía Model Context Protocol
      searxng_mcp_server.py
      rag_mcp_server.py
    graph.py            # build_agency_graph() — ensambla el StateGraph completo
  /gateway
    litellm_config.dev.yaml
    litellm_config.staging.yaml
    litellm_config.production.yaml
  /backend             # FastAPI: tenants, auth, endpoints, invoca el grafo
    /webhooks
      instagram_inbound.py  # captura DMs/comentarios con palabra clave (ver 7.9)
    /realtime
      sse_manager.py          # streaming de estado del grafo al dashboard
  /frontend             # Next.js dashboard
  /workers               # Celery tasks: render de video, publicación, métricas
  /knowledge              # documentos fuente del "cerebro" de marketing (sección 7), indexados en Qdrant
  docker-compose.yml       # levanta todo el stack local con un solo comando (ver 9.2)
  AGENTS.md
```

---

## 6. Arquitectura del sistema (resumen)

```
Next.js Dashboard ◄──SSE── FastAPI Backend ──► LangGraph (por tenant, thread_id = tenant_id)
        │  (aprobación humana)  │                     │
        └───────────────────────┘        ┌─────────────┼─────────────────────┐
                                          ▼                     ▼                     ▼
                                    Crew: Ideación        Crew: Guion            Crew: Edición*
                                    (MCP → SearXNG tool)  (MCP → RAG/Qdrant)     (*opcional, o
                                          │                     │               job de Celery)
                                          ▼                     ▼
                                    LiteLLM Proxy ◄──────────────┘
                                          │
                          ┌───────────────┼────────────────────┐
                          ▼               ▼                    ▼
                    Pool free-tier   Fallback pagado (1)   Ollama local (dev)

Instagram Graph API ──Webhook──► FastAPI /webhooks/instagram ──► Agente calificador de leads
   (comentario/DM con                                                    │
    palabra clave, ver 7.9)                                              ▼
                                                            Dashboard (lead + atribución a video_id)
```

Cada invocación del grafo corre con un `thread_id` único por tenant, lo que le da a LangGraph persistencia de estado independiente por cliente — esto es lo que hace posible pausar la ejecución en el checkpoint humano y reanudarla horas después sin perder contexto. El canal SSE es independiente del grafo: el backend emite eventos de progreso (`"Generando ideas..."` → `"Esperando aprobación"` → `"Editando video..."`) a medida que el thread avanza, sin que el dashboard tenga que hacer polling.

---

## 7. Conocimiento de dominio — el "cerebro" de marketing

Esto es lo que le da valor real al producto. Los prompts de los agentes (`role`, `goal`, `backstory` en CrewAI) deben reflejar esta lógica, no reinventarla libremente. Si se ajusta un umbral o una fórmula, se documenta el cambio aquí también.

### 7.1 Fórmula RUM (Relevancia Universal de Mercado)

Un contenido se vuelve viral cuando cruza el umbral de relevancia mínima de su nicho — no antes, sin importar cuánto valor aporte objetivamente. El umbral no es una constante universal: sube o baja según qué tan bueno sea, en promedio, el contenido que ya se publica en ese nicho.

```
RUM = U × I × C × S × D × A
```

- **U — Universalidad:** qué porcentaje de personas, sin contexto previo, entendería y se interesaría en el contenido.
- **I — Intensidad:** cuánto duele el problema o cuánto se desea el resultado que se promete.
- **C — Claridad:** si se entiende a la primera exposición, sin necesidad de releer o repetir.
- **S — Shareability:** si alguien lo reenviaría aunque no sea el comprador potencial.
- **D — Distribución:** si le interesaría incluso a alguien que jamás comprará (esas personas son las que lo empujan hacia audiencias nuevas).
- **A — Alineación:** si el cierre del contenido conecta específicamente con el cliente ideal real del negocio.

Cada variable se puntúa de 0.0 a 1.0. El umbral de descarte se calcula dinámicamente como un percentil sobre el histórico de RUM del propio nicho — **nunca** como número fijo hardcodeado en el código.

### 7.2 Filtro 5/50 (gate previo, barato)

Antes de gastar tokens en el scoring RUM completo, cada idea pasa por dos preguntas binarias:

1. ¿Lo entendería un niño de 5 años?
2. ¿Le interesaría a al menos 50 de cada 100 personas tomadas al azar en la calle?

Si cualquiera de las dos es "no", se descarta sin pasar al scorer RUM. Es la optimización de costo más simple del pipeline: elimina lo obviamente malo antes de la evaluación cara.

### 7.3 PPP — Promesa Principal de Producto

Plantilla base: **"Consigue [resultado] en [tiempo] sin [objeción principal]"**.

Checklist de validación:
- Cabe en una frase o frase y media (si no cabe, no está lista).
- El resultado es medible y concreto, no una sensación vaga.
- Tiene un tiempo definido — a menor tiempo con el mismo resultado percibido, mayor es el valor de la promesa.
- No usa jerga técnica del sector; el cliente no quiere el mecanismo, quiere el resultado.

### 7.4 Estructura de guion — 4 bloques

```json
{
  "gancho_0_5s": "decide en menos de 2 segundos si la persona se queda",
  "contexto_5_30s": "deliberadamente NO da la respuesta todavía — alarga la retención",
  "moraleja_30_50s": "la respuesta, idealmente reforzada con un caso de éxito real",
  "cta_50_60s": "palabra clave + acción concreta hacia un mensaje directo"
}
```

El error más común a evitar en la generación automática: que el agente entregue la respuesta en el gancho. La función del bloque de contexto es retener, no informar — el guionista_agent debe tratarlo explícitamente como relleno estructurado, no como contenido de relleno sin propósito.

### 7.5 Personaje de marca (una vez por tenant, no por video)

Se genera y persiste al inicio de la relación con cada cliente, y se inyecta como contexto fijo en todos los prompts de guion de ese tenant para mantener congruencia:

- 3 palabras que definan cómo quiere ser percibida la marca.
- Elementos visuales recurrentes (algo que se repita en cada video para generar asociación).
- Un objeto representativo que aparezca de forma consistente.

### 7.6 Triángulo PDH (para definir o validar el nicho de un cliente nuevo)

Sirve en el onboarding para confirmar que el nicho elegido por el cliente es sostenible, evaluando tres ejes del 1 al 10: **Pasión** (qué tanto le gusta genuinamente), **Dinero** (qué tan rentable es ese mercado) y **Habilidad** (qué tan bueno es realmente en eso). Un nicho fuerte en solo uno o dos ejes es una señal de alerta para el Account Manager, no algo que el sistema deba ignorar.

### 7.7 Análisis de competencia — cuatro cuadrantes de validación

Antes de dar por buena una idea, se contrasta contra referencias reales en cuatro combinaciones: dentro del nicho / fuera del nicho, y dentro de la plataforma de destino / fuera de ella. Esto es exactamente lo que resuelve la `Buscar_Tendencias_SearXNG` tool: el agente de ideación no debe inventar patrones — debe primero verificar si algo similar ya demostró tracción real en alguna de esas cuatro combinaciones.

### 7.8 Sistema 80/20 y clasificación Rojo/Amarillo/Verde

Después de publicar, cada video se clasifica según su ratio visitas/seguidores del tenant — nunca por un número absoluto de vistas, porque "viral" es relativo al tamaño de cada cuenta:

- **Rojo:** vistas por debajo de los seguidores actuales del tenant. Se descarta esa idea/estructura definitivamente.
- **Amarillo:** vistas alrededor o algo por encima de los seguidores. Se reintenta el mes siguiente en 1-2 formatos distintos (cambiando el ángulo, no la idea).
- **Verde:** al menos 10× los seguidores del tenant. Se reintenta en 2-3 formatos distintos, es la idea que más presupuesto de generación merece el mes siguiente.

Esta clasificación es lo que alimenta automáticamente el batch de ideación del mes siguiente: la mayoría del contenido nuevo debe partir de ideas ya validadas como amarillas o verdes, dejando solo una fracción del volumen mensual para ideas completamente nuevas sin validar.

Cuando el módulo de captura inbound (7.9) esté activo, esta clasificación debe ponderar también los leads generados por video, no solo el ratio de vistas — dos videos con el mismo ratio de vistas pueden tener una capacidad de conversión completamente distinta, y ese dato solo lo tiene el sistema de captura de DMs.

### 7.9 El embudo de conversión (inbound)

El Reel no vende — genera atención y filtra hacia una conversación privada. La conversión real ocurre cuando alguien comenta una palabra clave (por ejemplo "CONSULTA") en el video o responde a una story, y eso dispara un mensaje directo que abre la conversación. El sistema tiene que capturar ese momento en tiempo real, no en el batch de métricas de 72h — un lead frío pierde intención rápido.

Flujo:

1. El guion (7.4) siempre cierra con una palabra clave explícita y única en el CTA — no genérica ("escríbeme"), sino filtrable programáticamente y asociada a una campaña/idea concreta.
2. Instagram dispara un webhook a `POST /backend/webhooks/instagram_inbound.py` cuando alguien comenta o envía un DM que contiene esa palabra.
3. Un **agente calificador ligero** (no un Crew completo — este debe responder en segundos, no minutos) evalúa el mensaje: ¿la keyword coincide con una campaña activa del tenant? ¿hay contexto suficiente para saber de qué video vino? Si sí, lo enruta al dashboard como lead calificado con atribución completa (video de origen, keyword, timestamp, mensaje original).
4. **El agente calificador nunca cierra la venta.** Su único trabajo es filtrar ruido y preparar contexto para que el humano (Account Manager o el propio cliente) tome la conversación real — es la misma frontera deliberada que el checkpoint humano de publicación: el sistema prepara, la persona decide y vende.
5. Cada lead capturado se asocia al `video_id` de origen — sin esta atribución, es imposible saber qué contenido realmente genera negocio y no solo vistas (ver conexión con 7.8 arriba).

---

## 8. Reglas para agentes de código trabajando en este repo

- **Nunca** hardcodear API keys en código — todo vía variables de entorno y virtual keys de LiteLLM, una por tenant.
- **Nunca** agregar un segundo proveedor pagado al router de producción sin que quede documentado y decidido explícitamente en la sección 2 de este archivo — la regla de "un solo pagado" es una decisión de diseño, no un descuido.
- Todo nodo del grafo que publique contenido, gaste presupuesto de un tenant, o escriba en su nombre **debe** tener un `interrupt_before` de LangGraph antes de ejecutarse. Si añades un nodo nuevo con esas características y no lo pausas, es un bug, no una función.
- Todo contenido que venga de una búsqueda web debe pasar por el wrapper de sanitización antes de llegar al LLM — nunca HTML o JSON crudo de SearXNG directo al prompt. Ver `agents/tools/searxng_tool.py` como referencia del patrón (título + snippet recortado a ~400 caracteres, tags HTML removidos).
- `browser-use` es exclusivamente para tareas internas (investigación en sitios sin API pública). Nunca se usa para interactuar con la cuenta de Instagram de un cliente — eso siempre pasa por la Graph API oficial, sin excepción.
- Los umbrales de RUM y del filtro 5/50 no se hardcodean como constantes globales — se calculan por nicho y se guardan versionados en la base de datos, no en el código.
- Cualquier cambio a los prompts de `role`/`goal`/`backstory` de los agentes de CrewAI que toque la lógica de la sección 7 debe reflejarse también aquí, en AGENTS.md — este archivo y el código no pueden divergir.
- **Concurrencia en `dev`:** el entorno local de referencia es 4 núcleos / 16GB de RAM. Ollama, Postgres, Redis, Qdrant y FFmpeg compitiendo simultáneamente por esos recursos colapsan la máquina antes que cualquier límite de API. Los workers de Celery en `dev` se levantan siempre con `--concurrency=1`, y las tareas de procesamiento de video (moviepy/ffmpeg/Whisper) corren estrictamente en serie — un video a la vez, nunca en paralelo. Esta restricción se relaja solo en `staging`/`production` sobre hardware dimensionado para ello.
- **Seguridad de webhooks:** todo endpoint bajo `/backend/webhooks/` debe validar la firma `X-Hub-Signature-256` de Meta antes de procesar el payload, y el `hub.verify_token` del handshake inicial se guarda como variable de entorno, nunca en código. Un webhook sin validar es una puerta de entrada no autenticada al sistema — trátalo con el mismo cuidado que un endpoint de autenticación.
- **Tools compartidas → MCP:** cualquier herramienta que vaya a ser consumida por más de un agente o framework (`searxng_tool`, `rag_tool`) se expone como servidor MCP en `agents/mcp_servers/`, no como un `@tool` embebido directamente en el código de CrewAI. Los `@tool` en `agents/tools/` son el patrón legacy del prototipo inicial — no agregar herramientas nuevas ahí.

---

## 9. Configuración y orquestación local

### 9.1 Gateway por entorno

`AGENCY_ENV` controla qué `litellm_config.<env>.yaml` se carga:

```yaml
# litellm_config.dev.yaml — SOLO Ollama, cero riesgo de gasto
model_list:
  - model_name: motor-agencia
    litellm_params:
      model: ollama/qwen2.5-coder:7b
      api_base: "http://localhost:11434"
```

```yaml
# litellm_config.staging.yaml — pool gratuito real, sin fallback pagado
model_list:
  - model_name: motor-agencia
    litellm_params:
      model: groq/llama-3.3-70b-versatile
      api_key: "os.environ/GROQ_API_KEY"
  - model_name: motor-agencia
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: "os.environ/GEMINI_API_KEY"

router_settings:
  num_retries: 3
  cooldown_time: 300
```

```yaml
# litellm_config.production.yaml — pool gratuito + UN solo fallback pagado
model_list:
  - model_name: motor-agencia
    litellm_params:
      model: groq/llama-3.3-70b-versatile
      api_key: "os.environ/GROQ_API_KEY"
  - model_name: motor-agencia
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: "os.environ/GEMINI_API_KEY"
  - model_name: fallback-pagado
    litellm_params:
      model: "<elegir UNO — ver sección 2>"
      api_key: "os.environ/PAID_API_KEY"

router_settings:
  fallbacks: [{"motor-agencia": ["fallback-pagado"]}]
  num_retries: 3
  cooldown_time: 300

general_settings:
  master_key: "os.environ/LITELLM_MASTER_KEY"
  # una virtual key + budget mensual por tenant, generadas al onboarding
```

CrewAI y LangGraph nunca hablan directo con un proveedor — siempre apuntan a `OPENAI_API_BASE=http://localhost:4000/v1` (el proxy de LiteLLM), con la virtual key del tenant como `OPENAI_API_KEY`. Rotación, fallback y presupuesto ocurren completamente fuera de la lógica de los agentes.

### 9.2 `docker-compose.yml` — levantar todo con un solo comando

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: agency
      POSTGRES_PASSWORD: agency
      POSTGRES_DB: agency
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrantdata:/qdrant/storage

  searxng:
    image: searxng/searxng
    ports:
      - "8080:8080"
    volumes:
      - ./searxng-settings:/etc/searxng
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollamadata:/root/.ollama
    # solo estrictamente necesario cuando AGENCY_ENV=dev

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    ports:
      - "4000:4000"
    volumes:
      - ./gateway:/app/config
    command: ["--config", "/app/config/litellm_config.${AGENCY_ENV:-dev}.yaml"]
    env_file: .env
    depends_on:
      - ollama

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - redis
      - litellm
      - qdrant

  celery_worker:
    build: ./backend
    # concurrency=1 es obligatorio en dev — ver regla de concurrencia en sección 8
    command: celery -A worker worker --loglevel=info --concurrency=1
    env_file: .env
    depends_on:
      - redis
      - postgres

volumes:
  pgdata:
  qdrantdata:
  ollamadata:
```

Con `docker compose up -d` levantas Postgres, Redis, Qdrant, SearXNG, LiteLLM Proxy, el backend y el worker de Celery en un solo paso. `ollama` es parte del compose para que `dev` funcione sin tocar nada fuera de Docker, pero en `staging`/`production` puede quitarse del archivo sin afectar al resto.

---

## 10. Variables de entorno

```
AGENCY_ENV=dev|staging|production
LITELLM_PROXY_URL=http://localhost:4000/v1
LITELLM_MASTER_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
PAID_API_KEY=
SEARXNG_URL=http://localhost:8080
QDRANT_URL=http://localhost:6333
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379
S3_BUCKET=
INSTAGRAM_GRAPH_API_TOKEN=   # por tenant, nunca compartido entre clientes
```

---

## 11. Cómo probar

- Lógica del grafo (ramas, checkpoints, estado): correr en `AGENCY_ENV=dev` contra Ollama — validar la estructura del flujo sin gastar ni un token de un proveedor real.
- Comportamiento real de API (rate limits, fallback entre proveedores gratuitos): `AGENCY_ENV=staging` — aquí sí se detectan los 429 y se valida que el `cooldown_time` de LiteLLM funciona.
- Nunca correr tests automatizados contra `production` config ni contra la Graph API real de un cliente — usar una cuenta de Instagram de pruebas dedicada para cualquier test que llegue hasta el nodo de publicación.

```bash
AGENCY_ENV=dev pytest tests/
```

---

## 12. Roadmap

| Fase | Alcance |
|---|---|
| MVP interno | Un tenant (propio), grafo completo corriendo en `dev`, sin dashboard |
| Beta cerrada | Multi-tenant básico, `staging` validado con 3-5 clientes piloto |
| GA | `production` con fallback pagado activo, dashboard completo, billing por tenant |

---

## 13. Próximos archivos a construir (pendientes)

- `agents/graph.py` — versión completa del `build_agency_graph()` con los nodos de edición de video y publicación añadidos al esqueleto ya definido.
- `agents/mcp_servers/searxng_mcp_server.py` y `rag_mcp_server.py` — migrar el wrapper de sanitización (patrón ya definido) de `@tool` embebido a servidor MCP.
- `gateway/litellm_config.*.yaml` — los tres archivos por entorno (plantillas completas en sección 9.1).
- `docker-compose.yml` — ya definido completo en la sección 9.2; falta solo ajustar límites de recursos al hardware real de despliegue.
- `backend/webhooks/instagram_inbound.py` — receptor de webhooks con validación de firma (regla en sección 8) y el agente calificador de leads descrito en 7.9.
- `backend/realtime/sse_manager.py` — streaming de estado del grafo al dashboard (patrón en el diagrama de la sección 6).
- Migraciones SQL del modelo de datos multi-tenant — incluir tabla `leads` (`video_id`, `keyword`, `ig_user_id`, `mensaje_original`, `calificado_at`) para soportar 7.9.