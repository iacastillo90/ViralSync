"""
test_frontend_structure.py

Pruebas unitarias para validar la existencia y estructura de archivos del frontend Next.js 14.
"""

import os


def test_frontend_files_exist():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
    
    package_json = os.path.join(base_dir, "package.json")
    store_file = os.path.join(base_dir, "src", "stores", "useAgentStore.js")
    hook_file = os.path.join(base_dir, "src", "hooks", "useSSEStream.js")
    page_file = os.path.join(base_dir, "src", "app", "page.js")
    
    assert os.path.exists(package_json)
    assert os.path.exists(store_file)
    assert os.path.exists(hook_file)
    assert os.path.exists(page_file)
