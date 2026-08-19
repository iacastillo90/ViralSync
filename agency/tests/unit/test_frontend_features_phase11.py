"""
test_frontend_features_phase11.py

Pruebas unitarias para validar la totalidad del frontend (Fase 11: Cerebro, Admin, Onboarding, Public API).
"""

import os


def test_phase11_and_frontend_completion_files_exist():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    
    brain_view = os.path.join(base_dir, "features", "RAGBrain", "views", "BrainManagementView.jsx")
    public_api = os.path.join(base_dir, "features", "index.js")
    cerebro_page = os.path.join(base_dir, "app", "tenants", "[tenantId]", "cerebro", "page.js")
    nuevo_tenant_page = os.path.join(base_dir, "app", "tenants", "nuevo", "page.js")
    admin_sistema_page = os.path.join(base_dir, "app", "admin", "sistema", "page.js")
    
    assert os.path.exists(brain_view)
    assert os.path.exists(public_api)
    assert os.path.exists(cerebro_page)
    assert os.path.exists(nuevo_tenant_page)
    assert os.path.exists(admin_sistema_page)


def _read_frontend_file(relative_path):
    """Lee un archivo del frontend (src/) relativo a la raíz del repo."""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    full_path = os.path.join(base_dir, *relative_path.split("/"))
    assert os.path.exists(full_path), f"Archivo frontend faltante: {full_path}"
    with open(full_path, "r", encoding="utf-8") as fh:
        return fh.read()


def test_script_inspector_has_voice_persona_selector():
    """REQ-VOICE-04: ScriptInspectorView expone el selector 'Voz de persona'
    (catálogo desde GET /voice-personas) y dispara el PATCH de asignación."""
    content = _read_frontend_file("features/Scriptwriting/views/ScriptInspectorView.jsx")

    # Selector con etiqueta visible "Voz de persona"
    assert "Voz de persona" in content, "El inspector debe mostrar el selector 'Voz de persona'"
    # Catálogo de personas activas vía GET /voice-personas (useTenantResource)
    assert "voice-personas" in content, "El inspector debe listar el catálogo /voice-personas"
    # Asignación vía PATCH /scripts/{id}/voice-persona
    assert "voice-persona" in content, "El inspector debe PATCH /scripts/{id}/voice-persona"
    assert "PATCH" in content, "La asignación de voz debe usar el verbo PATCH"


def test_publish_approval_shows_voice_persona_badge():
    """REQ-VOICE-04: PublishApprovalView resuelve el nombre de la persona del
    guion desde el catálogo y lo muestra como badge aditivo (sin duplicar UI)."""
    content = _read_frontend_file("features/VideoPreview/views/PublishApprovalView.jsx")

    # Resuelve nombre de la persona desde GET /voice-personas
    assert "voice-personas" in content, "PublishApprovalView debe cargar el catálogo /voice-personas"
    # Badge aditivo sobre el campo expuesto por el script (scripts.py expone voice_persona_id)
    assert "voice_persona_name" in content, "Los items aprobables deben llevar el nombre de la persona"
