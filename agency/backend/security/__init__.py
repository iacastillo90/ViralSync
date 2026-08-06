"""
Módulo de Seguridad Backend de ViralSync.
Validación de firma HMAC SHA-256 para webhooks de Meta/Instagram.
"""

from .hmac_validator import verify_meta_hmac_signature

__all__ = ["verify_meta_hmac_signature"]
