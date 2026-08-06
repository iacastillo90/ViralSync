"""
Módulo de Webhooks Inbound de Meta / Instagram Graph API.
"""

from .instagram_inbound import process_instagram_webhook_payload

__all__ = ["process_instagram_webhook_payload"]
