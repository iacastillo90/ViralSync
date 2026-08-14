"""
test_auto_publisher.py

Pruebas unitarias para el worker de auto-publicación multi-canal (publisher_task.py).
"""

import pytest
import asyncio
from backend.db.session import init_db
from workers.publisher_task import _publish_to_instagram_reels, auto_publish_scheduled_videos_task


def test_publish_to_instagram_reels_mock():
    """Verifica que el flujo de publicación devuelva éxito simulado en entorno de prueba."""
    res = asyncio.run(_publish_to_instagram_reels(
        video_url="http://localhost:9000/viralsync-media/test.mp4",
        caption="Reel Test Caption"
    ))
    assert res["status"] == "success"
    assert "post_id" in res


def test_auto_publish_scheduled_videos_task_execution():
    """Verifica la ejecución síncrona de la tarea Celery de auto-publicación."""
    asyncio.run(init_db())
    res = auto_publish_scheduled_videos_task()
    assert res["status"] == "COMPLETED"
    assert "published_count" in res
