"""
test_locust_load_harness.py

Pruebas unitarias de contrato (TDD) para la Fase 3: Arnés de Pruebas de Carga Locust.
"""

from pathlib import Path


def test_locustfile_exists_and_valid():
    """REQ-LOAD-01: El archivo locustfile.py existe y contiene la clase ViralSyncUser."""
    locust_path = Path(__file__).parents[2] / "tests" / "load" / "locustfile.py"
    assert locust_path.exists(), "locustfile.py debe existir"
    content = locust_path.read_text(encoding="utf-8")
    assert "class ViralSyncUser" in content
    assert "def check_health" in content
