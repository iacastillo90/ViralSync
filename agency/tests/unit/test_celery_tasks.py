"""
test_celery_tasks.py

Pruebas unitarias para las tareas Celery en Eager Mode (ejecución síncrona).
"""

from workers.video_edit_task import process_video_postproduction
from workers.metrics_loop_task import audit_72h_metrics
from workers.celery_app import celery_app


def test_video_edit_task_eager_execution():
    """RELIABILITY-001: sin un render real, la tarea devuelve un fallo HONESTO
    (status 'failed', edited_video_uri=None) en lugar de fabricar una URL
    default p.ej. http://localhost:9000/.../default_rendered_output.mp4."""
    res = process_video_postproduction(
        tenant_id="tenant-demo-001",
        raw_video_uri="s3://viralsync-media-dev/tenant-demo-001/raw_input.mp4",
        script={"keyword": "CONSULTA"},
    )
    assert res["status"] == "failed"
    assert res.get("edited_video_uri") is None
    assert res.get("error")
    # Ninguna URL fabricada puede colarse como si fuera un render real
    assert "default_rendered_output.mp4" not in str(res)


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


def test_lead_persist_task_discoverable_and_routed_to_webhooks():
    """T-S1-05: persist_instagram_lead está registrada en Celery y ruteada a la cola 'webhooks'."""
    from workers.lead_persist_task import persist_instagram_lead
    from workers.celery_app import celery_app

    # Descubrible: registrada en el app de Celery tras el include.
    assert persist_instagram_lead.name in celery_app.tasks

    # Routed: la resolución real del router apunta a la cola webhooks (patrón DLQ).
    route = celery_app.amqp.router.route({}, persist_instagram_lead.name)
    queue = route.get("queue")
    assert getattr(queue, "name", queue) == "webhooks"


def test_publisher_task_registered_in_include():
    """REQ-PUB-03: el worker de auto-publicación está registrado en el
    include de Celery para que el beat pueda ejecutarlo."""
    assert "workers.publisher_task" in celery_app.conf.include


def test_publisher_task_daily_beat_schedule():
    """REQ-PUB-03, REQ-PUB-06: el beat diario dispara la auto-publicación a
    las 08:00 UTC (AUTO_PUBLISH_HOUR por defecto)."""
    beat = celery_app.conf.beat_schedule or {}
    entry = beat.get("auto-publish-daily")
    assert entry is not None, "Debe existir el entry 'auto-publish-daily'"
    assert (
        entry["task"] == "workers.publisher_task.auto_publish_scheduled_videos_task"
    ), "El beat debe apuntar a la tarea del publisher_task"
    assert entry["schedule"].hour == {8}, "Hora default 08:00 UTC"
    assert entry["schedule"].minute == {0}


def test_publisher_task_routed_to_default_queue():
    routes = celery_app.conf.task_routes or {}
    assert routes.get("workers.publisher_task.*") == {"queue": "default"}
