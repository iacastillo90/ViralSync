# 📄 DEVELOPERS.md — Guía de Supervivencia Local & Onboarding

## 🎯 Visión General & Filosofía Preventiva
ViralSync es un sistema distribuido que integra múltiples contenedores y servicios: **PostgreSQL 16**, **Redis 7**, **Qdrant**, **SearXNG**, **LiteLLM Proxy**, **Ollama**, **FastAPI**, **Celery Workers** y **Next.js 14**.

Para evitar asfixiar la estación de trabajo local (dimensionada para **4 núcleos / 16GB RAM**), esta guía establece el **orden exacto de encendido**, los límites de concurrencia y las reglas estrictas de hardware para garantizar una ejecución fluida sin congelamientos del sistema operativo.

---

## ⚡ 1. Orden Exacto de Encendido (Paso a Paso)

Sigue estrictamente esta secuencia al iniciar tu jornada de desarrollo para asegurar la disponibilidad de dependencias en cascada:

```
[Paso 1: Docker Base] ➔ [Paso 1.5: Pull Ollama] ➔ [Paso 1.8: Activar venv] ➔ [Paso 2: Migraciones DB] ➔ [Paso 3: Ingesta RAG]
                                                                                                                │
[Paso 6: Frontend Next.js] ◄────────────── [Paso 5: Celery Worker] ◄────────────── [Paso 4: Backend FastAPI] ◄──┘
```

### Paso 1: Levantar Servicios Base con Docker
```bash
# Levantar PostgreSQL, Redis, Qdrant, SearXNG, Ollama y LiteLLM Proxy
docker compose up -d postgres redis qdrant searxng ollama litellm
```
*Verifica que los servicios estén activos antes de continuar:*
```bash
docker compose ps
```

### Paso 1.5: Descargar Modelo Local en Ollama (Solo primera vez)
El contenedor de Ollama inicia vacío. Debes descargar el modelo especificado en `litellm_config.dev.yaml`:
```bash
docker exec -it ollama ollama pull qwen2.5-coder:7b
```

### Paso 1.8: Activar Entorno Virtual Python & Dependencias
Antes de ejecutar FastAPI o Celery en Python, activa tu entorno virtual e instala los paquetes:
```bash
# Activar entorno virtual
source venv/bin/activate  # En Linux/Mac
# venv\Scripts\activate   # En Windows

# Instalar dependencias del proyecto
pip install -r requirements.txt
```

### Paso 2: Ejecutar Migraciones de PostgreSQL
```bash
# Cargar el esquema SQL inicial multi-tenant
psql -h localhost -U agency -d agency -f agency/migrations/001_init_schema.sql
```

### Paso 3: Cargar el "Cerebro RAG" en Qdrant
```bash
# Vectorizar e indexar documentos de estrategia en Qdrant (colección marketing_brain)
python agency/knowledge/ingest_knowledge.py
```

### Paso 4: Levantar el Servidor Backend FastAPI
```bash
# Iniciar servidor REST + Webhooks Meta + SSE Realtime en el puerto 8000
AGENCY_ENV=dev uvicorn agency.backend.main:app --reload --port 8000
```

### Paso 5: Levantar Worker de Celery (Regla de Concurrencia Serializada)
```bash
# IMPORTANTE: --concurrency=1 es obligatorio en desarrollo (AGENTS.md sección 8)
AGENCY_ENV=dev celery -A agency.workers.celery_app worker --loglevel=info --concurrency=1
```

### Paso 6: Levantar el Dashboard Frontend Next.js
```bash
# Iniciar servidor de desarrollo de Next.js en puerto 3000
cd agency/frontend
npm run dev
```

---

## 🔒 2. Plantilla `.env.example`

Copia este contenido en un archivo `.env` en la raíz del proyecto (`/home/ivan/Desktop/AgentMarketingIA/.env`):

```ini
# ===================================================================== #
# VIRALSYNC ENVIRONMENT CONFIGURATION
# ===================================================================== #

# Entorno de ejecución: dev | staging | production
AGENCY_ENV=dev

# --------------------------------------------------------------------- #
# Gateway LiteLLM Proxy
# --------------------------------------------------------------------- #
LITELLM_PROXY_URL=http://localhost:4000/v1
LITELLM_MASTER_KEY=sk-litellm-master-key-dev

# API Keys para Staging / Production (Opcionales en Dev con Ollama)
GROQ_API_KEY=
GEMINI_API_KEY=
PAID_API_KEY=

# --------------------------------------------------------------------- #
# Base de Datos & Caché / Cola
# --------------------------------------------------------------------- #
DATABASE_URL=postgresql://agency:agency@localhost:5432/agency
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
SEARXNG_URL=http://localhost:8080

# --------------------------------------------------------------------- #
# Integraciones Meta / Instagram Graph API
# --------------------------------------------------------------------- #
INSTAGRAM_WEBHOOK_VERIFY_TOKEN=token_verificacion_meta_dev
INSTAGRAM_APP_SECRET=secreto_meta_app_dev

# --------------------------------------------------------------------- #
# Almacenamiento S3 / R2 (Video Crudo y Editado)
# --------------------------------------------------------------------- #
S3_BUCKET=viralsync-media-dev
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# --------------------------------------------------------------------- #
# Frontend Next.js (Variables accesibles en el cliente)
# --------------------------------------------------------------------- #
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SSE_URL=http://localhost:8000/realtime/sse
NEXT_PUBLIC_ENV=dev
```

---

## 🛠️ 3. Comandos de Administración & Mantenimiento

### Simular Webhooks de Instagram en Local (Ngrok)
Para que Meta pueda enviar eventos reales de DMs y comentarios a tu entorno `dev`:
1. Expón el puerto de FastAPI al internet público:
```bash
ngrok http 8000
```
2. Copia la URL HTTPS generada (ej: `https://abcd-12-34.ngrok-free.app`).
3. Úsala en el panel de Facebook Developers apuntando a: `https://abcd-12-34.ngrok-free.app/webhooks/instagram`.
4. Asegúrate de que el `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` coincida con tu `.env`.

---

### Reiniciar Base de Datos Local
```bash
# Reaplicar migraciones desde cero
psql -h localhost -U agency -d agency -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -h localhost -U agency -d agency -f agency/migrations/001_init_schema.sql
```

---

### Probar Ingesta RAG en Qdrant
```bash
python agency/knowledge/ingest_knowledge.py
```

---

### Ejecutar Suite de Pruebas Automatizadas
```bash
# Ejecutar pytest en modo dev sin gastar tokens
AGENCY_ENV=dev pytest agency/tests/
```

---

## 🛑 4. Reglas Estrictas de Hardware & Concurrencia

1. **Celery Worker Serializado (`--concurrency=1`):**
   - **REGLA NO NEGOCIABLE:** En `AGENCY_ENV=dev`, Celery **siempre** se arranca con `--concurrency=1`.
   - Las tareas de edición de video con FFmpeg, MoviePy y Whisper son intensivas en CPU/RAM. Ejecutarlas en serie garantiza que el sistema operativo no colapse.

2. **Uso de Ollama Local en Dev:**
   - En `AGENCY_ENV=dev`, el router LiteLLM apunta exclusivamente a Ollama (`qwen2.5-coder:7b` / `llama3.2`). No consumir tokens de APIs pagadas durante desarrollo.

3. **Cero Polling HTTP en Frontend:**
   - El dashboard Next.js debe consumir eventos exclusivamente a través de la suscripción **SSE** (`/realtime/sse/{tenant_id}`) manejada por **Zustand**. Está prohibido usar `setInterval` para consultar el estado del grafo.
