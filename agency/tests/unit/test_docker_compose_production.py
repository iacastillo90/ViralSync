"""
test_docker_compose_production.py

Pruebas unitarias para verificar la configuración del manifiesto docker-compose.production.yml (REQ-DCS-01).
"""

import os
import yaml
import pytest

COMPOSE_PATH = os.path.join(os.path.dirname(__file__), "../../docker-compose.production.yml")


def test_docker_compose_production_file_exists():
    """Verifica que docker-compose.production.yml exista y sea un YAML válido."""
    assert os.path.exists(COMPOSE_PATH)
    with open(COMPOSE_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert "services" in config
    assert "backend" in config["services"]


def test_docker_compose_production_has_segregated_celery_workers():
    """Verifica la definición de servicios Celery segregados (-Q default, -Q rendering, -Q webhooks)."""
    with open(COMPOSE_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    services = config["services"]
    
    assert "celery_worker_default" in services
    assert "celery_worker_rendering" in services
    assert "celery_worker_webhooks" in services
    
    assert "-Q default" in services["celery_worker_default"]["command"]
    assert "-Q rendering" in services["celery_worker_rendering"]["command"]
    assert "-Q webhooks" in services["celery_worker_webhooks"]["command"]
