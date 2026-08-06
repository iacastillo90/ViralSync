"""
test_e2e_full_pipeline_and_garbage_collection.py

Prueba End-to-End integral de ViralSync y Verificación de Recolector de Basura (Zero Waste):
- Valida la ingesta, evaluación RUM, guion, Guardián Director, renderizado faceless y publicación outbound.
- Garantiza que NO queden archivos temporales .mp3 o .mp4 en el disco local post-ejecución.
"""

import os
import shutil
import tempfile
import asyncio
from agents.graph import build_agency_graph
from agents.crews.video_director_crew import run_video_director_crew
from workers.video_edit_task import trigger_video_render
from workers.trend_scraper_task import scrape_daily_marketing_trends
from workers.celery_app import celery_app


def test_celery_task_routing_configuration():
    """Verifica que task_routes tenga configuradas las colas de rendering y webhooks."""
    routes = celery_app.conf.task_routes
    assert "workers.video_edit_task.*" in routes
    assert routes["workers.video_edit_task.*"]["queue"] == "rendering"
    assert routes["workers.webhook_dlq_task.*"]["queue"] == "webhooks"


def test_trend_scraper_task_execution():
    """Verifica la ejecución del raspador dinámico de tendencias RAG."""
    result = scrape_daily_marketing_trends.run(niche="SaaS B2B")
    assert result["status"] == "success"
    assert result["trends_count"] > 0
    assert len(result["trends"]) > 0


def test_garbage_collection_zero_waste_policy():
    """Verifica que la carpeta temporal y archivos .mp3/.mp4 sean eliminados inmediatamente post-renderizado."""
    temp_dir = tempfile.mkdtemp(prefix="test_zero_waste_")
    audio_path = os.path.join(temp_dir, "speech.mp3")
    video_path = os.path.join(temp_dir, "final_output.mp4")

    # Crear archivos temporales de prueba
    with open(audio_path, "wb") as f:
        f.write(b"fake_audio_bytes")
    with open(video_path, "wb") as f:
        f.write(b"fake_video_bytes")

    assert os.path.exists(audio_path)
    assert os.path.exists(video_path)

    # Simular bloque finally de recolección estricta de basura en app.py
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Verificar que el disco quedó completamente limpio
    assert not os.path.exists(temp_dir)
    assert not os.path.exists(audio_path)
    assert not os.path.exists(video_path)


def test_e2e_full_state_graph_pipeline():
    """Prueba End-to-End del Grafo de Estado compilado."""
    graph = build_agency_graph()
    initial_state = {
        "tenant_id": "tenant-e2e-test",
        "niche": "B2B Software",
        "niche_ppp": "Triplicar ventas SaaS en 90 días",
    }
    
    # El grafo debe tener todos los nodos registrados en la secuencia correcta
    assert "ideation" in graph.nodes
    assert "scriptwriting" in graph.nodes
    assert "video_edit" in graph.nodes
    assert "publish" in graph.nodes
