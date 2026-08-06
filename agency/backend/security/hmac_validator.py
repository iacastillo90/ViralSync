"""
hmac_validator.py

Validador de firma de seguridad HMAC SHA-256 (X-Hub-Signature-256) de Meta.
Garantiza la autenticidad del payload de webhooks en tiempo constante para prevenir timing attacks.
"""

import hmac
import hashlib


def verify_meta_hmac_signature(
    payload_bytes: bytes, signature_header: str, app_secret: str
) -> bool:
    """
    Verifica si la firma enviada por Meta en X-Hub-Signature-256 es válida.
    
    :param payload_bytes: Contenido del cuerpo HTTP en bytes crudos.
    :param signature_header: Valor de la cabecera 'X-Hub-Signature-256' (ej: 'sha256=1a2b3c...').
    :param app_secret: Secreto de la aplicación Meta guardado en .env (INSTAGRAM_APP_SECRET).
    :return: True si la firma es auténtica, False en caso contrario.
    """
    if not payload_bytes or not signature_header or not app_secret:
        return False

    if not signature_header.startswith("sha256="):
        return False

    received_hash = signature_header.replace("sha256=", "").strip()

    expected_hash = hmac.new(
        app_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(received_hash.lower(), expected_hash.lower())
