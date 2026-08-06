"""
test_celery_tasks.py

Pruebas unitarias para las tareas Celery en Eager Mode (ejecución síncrona).
"""

from workers.video_edit_task import process_video_postproduction
from workers.metrics_loop_task import audit_72h_metrics


def test_video_edit_task_eager_execution():
    res = process_video_postproduction(
        tenant_id="tenant-demo-001",
        raw_video_uri="s3://viralsync-media-dev/tenant-demo-001/raw_input.mp4",
        script={"keyword": "CONSULTA"},
    )
    assert res["status"] == "completed"
    assert "edited_video_uri" in res


def test_metrics_loop_task_verde():
    res = audit_72h_metrics(
        tenant_id="tenant-demo-001",
        video_id="video-55",
        views=150000,
        followers=10000,
    )
    assert res["classification"] == "VERDE"
    assert res["ratio"] == 15.0


def test_metrics_loop_task_rojo():
    res = audit_72h_metrics(
        tenant_id="tenant-demo-001",
        video_id="video-56",
        views=4500,
        followers=10000,
    )
    assert res["classification"] == "ROJO"
    assert res["ratio"] == 0.45
