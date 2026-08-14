"""
test_script_exporter.py

Pruebas unitarias para la exportación de paquete creativo ZIP (Fase 1C).
"""

import zipfile
import io
import json
from backend.services.script_exporter import create_script_export_zip, build_scene_prompts, generate_post_caption


def test_build_scene_prompts():
    script = {
        "gancho_0_5s": "¿Sabías que el 90% comete este error?",
        "contexto_5_30s": "Contexto de prueba...",
        "moraleja_30_50s": "Solución de prueba...",
        "cta_50_60s": "Comenta CLAVE",
        "keyword": "CLAVE",
    }
    prompts = build_scene_prompts(script)
    assert len(prompts) == 6
    assert prompts[0]["time"] == "0-5s"
    assert "CLAVE" in prompts[5]["prompt"]


def test_generate_post_caption():
    script = {
        "gancho_0_5s": "Gancho demo",
        "contexto_5_30s": "Contexto demo",
        "moraleja_30_50s": "Moraleja demo",
        "cta_50_60s": "CTA demo",
        "keyword": "OFERTA",
    }
    caption = generate_post_caption(script)
    assert "OFERTA" in caption
    assert "#ViralSync" in caption


def test_create_script_export_zip():
    script = {
        "id": "12345678-1234-1234-1234-123456789012",
        "gancho_0_5s": "Gancho de prueba",
        "contexto_5_30s": "Contexto de prueba",
        "moraleja_30_50s": "Moraleja de prueba",
        "cta_50_60s": "CTA de prueba",
        "keyword": "DESCUENTO",
        "trend_score": 85,
    }
    video_dummy = b"fake_video_bytes_content"

    zip_bytes = create_script_export_zip(script, video_bytes=video_dummy)
    assert len(zip_bytes) > 0

    # Verificar contenidos del ZIP generado
    buf = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buf, "r") as zf:
        names = zf.namelist()
        assert "guion.txt" in names
        assert "guion.json" in names
        assert "prompts_escenas.json" in names
        assert "descripcion_post.txt" in names
        assert "video.mp4" in names

        json_data = json.loads(zf.read("guion.json").decode("utf-8"))
        assert json_data["keyword"] == "DESCUENTO"
        assert zf.read("video.mp4") == video_dummy
