# Dockerfile para el Backend FastAPI y el Worker Celery de ViralSync.
# Ambos servicios usan la misma imagen base; el CMD se sobreescribe en docker-compose.yml.
#
# Razón de creación (Fase 6): docker-compose.yml hacía build: . desde agency/
# sin que existiera este archivo, causando un error fatal al intentar construir la imagen.

FROM python:3.12-slim

# Instalación de dependencias del sistema necesarias para psycopg2 y herramientas HTTP.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar primero solo requirements para aprovechar el cache de capas de Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente.
COPY agency/ .

# Puerto por defecto del backend FastAPI.
EXPOSE 8000

# CMD por defecto para el servicio backend.
# El servicio celery_worker sobreescribe este CMD en docker-compose.yml.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
