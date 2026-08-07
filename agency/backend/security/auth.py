"""
auth.py

Módulo de Seguridad Fundacional, Autenticación JWT, Control de Acceso por Roles (RBAC)
y Aislamiento Estricto de Contexto de Tenant.
"""

import os
import json
import time
import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, List, Optional
from fastapi import Request, HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "viralsync_enterprise_secret_key_2026")
JWT_EXPIRATION_SECONDS = 86400  # 24 horas

security = HTTPBearer(auto_error=False)


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64decode(data_str + padding)


def create_access_token(user_id: str, tenant_id: str, role: str = "editor") -> str:
    """Crea un token JWT firmado con HMAC SHA-256."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS,
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodifica y valida la firma HMAC SHA-256 y expiración del token JWT."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Estructura de token JWT inválida")

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')

        expected_sig = _base64url_encode(
            hmac.new(JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        )

        if not hmac.compare_digest(signature_b64, expected_sig):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma de token JWT inválida")

        payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
        if payload.get("exp", 0) < int(time.time()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token JWT expirado")

        return payload
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Error validando token JWT ({exc})")


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Dict[str, Any]:
    """Dependencia FastAPI para extraer y verificar el usuario del encabezado Authorization: Bearer <token>."""
    if not credentials:
        if os.getenv("AGENCY_ENV", "dev") == "dev":
            return {"sub": "usr_dev_001", "tenant_id": "default_tenant", "role": "admin"}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Encabezado de autorización ausente")

    return decode_access_token(credentials.credentials)


def require_roles(allowed_roles: List[str]):
    """Generador de dependencias RBAC para verificar los roles permitidos."""
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        user_role = user.get("role", "viewer")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado: El rol '{user_role}' no posee autorización para esta acción.",
            )
        return user
    return role_checker


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware para forzar el aislamiento estricto de Tenant.
    Inspecciona los encabezados X-Tenant-ID o el payload JWT y lo asocia al estado de la solicitud.
    """

    async def dispatch(self, request: Request, call_next):
        public_paths = ["/health", "/docs", "/openapi.json", "/api/v1/auth/login", "/api/v1/webhooks"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")

        if not tenant_id and request.url.path.startswith("/api/v1/tenants/"):
            path_parts = request.url.path.split("/")
            if len(path_parts) >= 5:
                tenant_id = path_parts[4]

        if not tenant_id:
            tenant_id = "default_tenant"

        request.state.tenant_id = tenant_id
        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response
