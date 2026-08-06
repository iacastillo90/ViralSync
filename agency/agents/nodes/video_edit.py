"""
Nodo de edición de video.

El humano graba con el guion (script) y sube el crudo a S3/R2. Este nodo
NO edita en el proceso del grafo — encola un job de Celery
(workers/video_edit_task.py) que aplica, en este orden:

  1. Limpieza de silencios muertos (moviepy, sobre la pista de audio).
  2. Transcripción + subtítulos quemados (Whisper) — legibles, 2-3 palabras
     por línea, fuente única (ver clase de Marcos en la transcripción:
     "menos es más, mientras más legible mejor").
  3. Inserción de B-roll usando las keywords que extrajo el agente de
     Cerebras a partir del guion.
  4. SFX/interrupciones de patrón cada 5-15s (AGENTS.md 7.4, punto 5 de la
     clase de edición: pattern interrupts).

El grafo espera el resultado de forma asíncrona (polling corto o webhook
interno de Celery) antes de avanzar al checkpoint de publicación.
"""

from workers.video_edit_task import edit_video_task


def run(state: dict) -> dict:
    tenant_id = state["tenant_id"]
    script = state["script"]
    raw_uri = state["raw_video_uri"]

    if not raw_uri:
        return {"errors": ["No hay video crudo subido todavía — el humano debe grabar primero."]}

    async_result = edit_video_task.delay(tenant_id=tenant_id, raw_uri=raw_uri, script=script)
    edited_uri = async_result.get(timeout=None)  # el worker corre en serie en dev, ver AGENTS.md sección 8

    return {"edited_video_uri": edited_uri, "publish_approval_status": "pending"}
