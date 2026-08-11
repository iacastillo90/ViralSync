"""
test_frontend_hardening_contract.py

Pruebas unitarias para validar el contrato de frontend hardening (REQ-FIH-01/02).
"""

import os
import pytest


def test_api_config_js_file_contains_presigned_and_429_handling():
    """Verifica que apiConfig.js exporte la lógica presigned upload y el desglose de 429 Retry-After."""
    api_config_path = os.path.join(os.path.dirname(__file__), "../../frontend/src/services/apiConfig.js")
    assert os.path.exists(api_config_path)
    with open(api_config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "getPresignedUploadUrl" in content
    assert "uploadFileWithPresignedUrl" in content
    assert "retryAfter" in content
    assert "429" in content
