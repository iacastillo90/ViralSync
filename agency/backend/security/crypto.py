"""
crypto.py

Bóveda de cifrado simétrico para tokens OAuth de redes sociales (REQ-OVE-01).
Utiliza Fernet (AES-128-CBC / HMAC-SHA256) derivado de OAUTH_ENCRYPTION_KEY o JWT_SECRET_KEY.
"""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

_OAUTH_KEY_RAW = os.getenv(
    "OAUTH_ENCRYPTION_KEY",
    os.getenv("JWT_SECRET_KEY", "agency-dev-secret-key-change-in-production-32b"),
)

def _derive_fernet_key(passphrase: str) -> bytes:
    """Deriva una clave válida Fernet (32-bytes base64url) desde un passphrase."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"viralsync_oauth_salt_static",
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))

_cipher_suite = Fernet(_derive_fernet_key(_OAUTH_KEY_RAW))


def encrypt_token(plain_token: Optional[str]) -> Optional[str]:
    """Cifra un token de acceso OAuth a un ciphertext seguro en Base64url."""
    if not plain_token:
        return plain_token
    try:
        encrypted_bytes = _cipher_suite.encrypt(plain_token.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as exc:
        logger.error(f"Error encriptando token OAuth: {exc}")
        raise RuntimeError(f"Fallo de encriptación de token: {exc}") from exc


def decrypt_token(cipher_text: Optional[str]) -> Optional[str]:
    """Descifra un ciphertext OAuth y retorna el token original en plano."""
    if not cipher_text:
        return cipher_text
    try:
        decrypted_bytes = _cipher_suite.decrypt(cipher_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as exc:
        logger.error(f"Error desencriptando token OAuth: {exc}")
        raise ValueError(f"Fallo al desencriptar token OAuth: ciphertext inválido ({exc})") from exc
