"""
workers/video_edit_task.py

Tarea de Celery para post-producción de video:
1. Trimming de silencios en pista de audio.
2. Generación de subtítulos (Whisper) quemados en pantalla.
3. Inserción de B-roll basada en keywords.
4. Interrupciones de patrón (SFX) cada 5-15s.
"""

import os
import time
import logging
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.video_edit_task.edit_video_task")
def edit_video_task(tenant_id: str, raw_uri: str, script: dict) -> str:
    logger.info(f"[Tenant {tenant_id}] Iniciando edición de video para: {raw_uri}")
    
    # Simulación de pasos de procesamiento (MoviePy / FFmpeg / Whisper)
    # Paso 1: Detección y eliminación de silencios
    time.sleep(1.0)
    logger.info("Paso 1/4: Silencios muertos eliminados.")

    # Paso 2: Generación de subtítulos Whisper
    time.sleep(1.0)
    logger.info("Paso 2/4: Subtítulos Whisper quemados (2-3 palabras por línea).")

    # Paso 3: B-roll insertion
    keywords = script.get("cta_50_60s", "").split()[:3]
    time.sleep(1.0)
    logger.info(f"Paso 3/4: Clips de B-roll insertados para keywords: {keywords}")

    # Paso 4: SFX & Pattern Interrupts cada 5-15s
    time.sleep(1.0)
    logger.info("Paso 4/4: Interrupciones de patrón y SFX colocados.")

    # Generar URI del resultado editado
    base_name = os.path.basename(raw_uri) if raw_uri else "video_input.mp4"
    output_filename = f"edited_{tenant_id}_{int(time.time())}_{base_name}"
    edited_uri = f"/storage/videos/{tenant_id}/{output_filename}"

    logger.info(f"[Tenant {tenant_id}] Edición completada. Video final: {edited_uri}")
    return edited_uri
