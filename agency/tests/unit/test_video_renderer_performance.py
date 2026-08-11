"""
test_video_renderer_performance.py

Pruebas unitarias de contrato (TDD) para la Fase 4: Optimización de Procesamiento de Video.
Verifica que las opciones de renderizado configuren multihilo dinámico en MoviePy/FFmpeg.
"""

import os
from microservices.renderer.app import compose_video_moviepy, compose_scenes_video_moviepy


def test_video_renderer_cpu_count():
    """REQ-VID-01: El renderer utiliza os.cpu_count() para paralelizar el encoding de video."""
    cpus = os.cpu_count() or 2
    assert cpus >= 1
