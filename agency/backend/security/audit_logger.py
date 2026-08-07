"""
audit_logger.py

Módulo de Auditoría Enterprise (Audit Logging) para registrar acciones administrativas
y cambios de estado críticos por tenant.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("enterprise_audit")


def log_audit_event(
    tenant_id: str, user_id: str, action: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Registra una entrada de auditoría inmutable."""
    audit_entry = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "details": details or {},
        "timestamp": int(time.time()),
    }

    logger.info(f"AUDIT LOG | Tenant: {tenant_id} | User: {user_id} | Action: {action} | Details: {details}")
    return audit_entry
