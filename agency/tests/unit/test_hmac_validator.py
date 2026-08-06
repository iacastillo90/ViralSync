"""
test_hmac_validator.py

Pruebas unitarias TDD para la validación de firmas HMAC SHA-256 de Meta webhooks.
"""

import hmac
import hashlib
from backend.security.hmac_validator import verify_meta_hmac_signature


def test_verify_meta_hmac_signature_valid():
    secret = "secreto_meta_test_secret"
    payload = b'{"object":"instagram","entry":[]}'
    
    expected_hash = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    signature_header = f"sha256={expected_hash}"

    assert verify_meta_hmac_signature(payload, signature_header, secret) is True


def test_verify_meta_hmac_signature_invalid_secret():
    secret = "secreto_meta_test_secret"
    wrong_secret = "secreto_incorrecto"
    payload = b'{"object":"instagram","entry":[]}'
    
    expected_hash = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    signature_header = f"sha256={expected_hash}"

    assert verify_meta_hmac_signature(payload, signature_header, wrong_secret) is False


def test_verify_meta_hmac_signature_tampered_payload():
    secret = "secreto_meta_test_secret"
    payload = b'{"object":"instagram","entry":[]}'
    tampered_payload = b'{"object":"instagram","entry":[{"tampered":true}]}'
    
    expected_hash = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    signature_header = f"sha256={expected_hash}"

    assert verify_meta_hmac_signature(tampered_payload, signature_header, secret) is False


def test_verify_meta_hmac_signature_malformed_header():
    secret = "secreto_meta_test_secret"
    payload = b'{"object":"instagram","entry":[]}'
    
    # Missing 'sha256=' prefix
    invalid_header = "1a2b3c4d"
    assert verify_meta_hmac_signature(payload, invalid_header, secret) is False
