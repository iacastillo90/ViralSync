"""
test_oauth_vault.py

Pruebas unitarias para la bóveda de cifrado simétrico OAuth (crypto.py) y validaciones Pydantic (REQ-OVE-01/02).
"""

import pytest
from pydantic import ValidationError
from backend.security.crypto import encrypt_token, decrypt_token
from backend.routers.graph_execution import GraphRunRequest


def test_crypto_encrypt_and_decrypt():
    """Verifica que encrypt_token y decrypt_token mantengan simetría total."""
    token_original = "EAAG1234567890abcdef_secret_oauth_token"
    
    cipher = encrypt_token(token_original)
    assert cipher != token_original
    assert isinstance(cipher, str)
    
    plain = decrypt_token(cipher)
    assert plain == token_original


def test_crypto_handles_none_and_empty():
    """Verifica que tokens vacíos o None se manejen sin excepciones."""
    assert encrypt_token(None) is None
    assert encrypt_token("") == ""
    assert decrypt_token(None) is None
    assert decrypt_token("") == ""


def test_crypto_invalid_cipher_raises_value_error():
    """Verifica que un ciphertext inválido lance ValueError."""
    with pytest.raises(ValueError, match="ciphertext inválido"):
        decrypt_token("ciphertext_totalmente_invalido")


def test_graph_run_request_validates_tokens():
    """Verifica que GraphRunRequest rechace tokens vacíos o demasiado cortos (RELIABILITY-005)."""
    # Token válido pasa
    req = GraphRunRequest(ig_access_token="token_valido_123")
    assert req.ig_access_token == "token_valido_123"
    
    # Token vacío o con solo espacios falla
    with pytest.raises(ValidationError):
        GraphRunRequest(ig_access_token="   ")
        
    # Token menor a 5 caracteres falla
    with pytest.raises(ValidationError):
        GraphRunRequest(tiktok_access_token="abc")
