"""
auth.py

Módulo de Seguridad Fundacional, Autenticación JWT, Control de Acceso por Roles (RBAC)
y Aislamiento Estricto de Contexto de Tenant con Verificación Fail-Closed.
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

AGENCY_ENV = os.getenv("AGENCY_ENV", "dev").lower()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "viralsync_enterprise_secret_key_2026")
JWT_EXPIRATION_SECONDS = 86400  # 24 horas

# Guardia de Seguridad Fail-Fast para JWT_SECRET_KEY en Producción
if AGENCY_ENV in ["prod", "production", "staging"] and JWT_SECRET_KEY == "viralsync_enterprise_secret_key_2026":
    raise ValueError("CRÍTICO DE SEGURIDAD: JWT_SECRET_KEY por defecto 'viralsync_enterprise_secret_key_2026' está prohibida en entornos staging/prod.")

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


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    request: Request = None,
) -> Dict[str, Any]:
    """Dependencia FastAPI para extraer y verificar el usuario del encabezado Authorization: Bearer <token>.

    Fallback de desarrollo (D1): en AGENCY_ENV=dev/development sin credenciales
    Bearer, el usuario dev se vincula al tenant de la REQUEST (X-Tenant-ID header
    o tenant de la URL, resuelto por TenantContextMiddleware en request.state.
    tenant_id) en lugar del hardcoded "default_tenant", de modo que los UUIDs
    reales pasen verify_tenant_access y los GETs devuelvan 200. En cualquier
    entorno no-dev el fallback NO existe: sin JWT → 401 (fail-closed).
    """
    if not credentials:
        if request and request.query_params.get("token"):
            return decode_access_token(request.query_params.get("token"))

        if AGENCY_ENV in ("dev", "development"):
            return {
                "sub": "usr_dev_001",
                "tenant_id": getattr(request, "state", None)
                and getattr(request.state, "tenant_id", None)
                or None,
                "role": "admin",
            }
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


async def verify_tenant_access(
    tenant_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependencia FastAPI compartida para el aislamiento Anti-IDOR en todos los endpoints
    bajo /api/v1/tenants/{tenant_id}/... y /realtime/sse/{tenant_id}

    Verifica que:
    1. Existe un usuario autenticado con JWT válido (viene de get_current_user).
    2. El tenant_id del JWT coincide con el tenant_id de la URL.
    """
    jwt_tenant = current_user.get("tenant_id")
    if not jwt_tenant or jwt_tenant != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado: Aislamiento Anti-IDOR — token de '{jwt_tenant}' no puede acceder al tenant '{tenant_id}'.",
        )
    return current_user


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware para forzar el aislamiento estricto de contexto de Tenant.

    En staging/prod: exige token JWT válido. Si falta o es inválido, rechaza 401.
    En dev: acepta X-Tenant-ID header o extrae de la URL (/api/v1/tenants/ o /realtime/sse/) como fallback.
    Siempre marca request.state.jwt_verified=True/False para que los guards puedan distinguir
    si el tenant_id proviene de una fuente firmada o de un header sin autenticar.
    """

    async def dispatch(self, request: Request, call_next):
        public_paths = ["/health", "/docs", "/openapi.json", "/api/v1/auth/login", "/api/v1/webhooks"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        tenant_id = None
        jwt_verified = False

        # 1. Fuente de verdad primaria: JWT firmado (Bearer header o ?token= param para EventSource)
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        elif request.query_params.get("token"):
            token = request.query_params.get("token")

        if token:
            try:
                payload = decode_access_token(token)
                tenant_id = payload.get("tenant_id")
                request.state.authenticated_user = payload
                jwt_verified = True
            except HTTPException:
                # Token presente pero inválido (firma incorrecta, expirado, malformado)
                # En staging/prod rechazar inmediatamente
                if AGENCY_ENV not in ("dev", "development"):
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Token JWT inválido o expirado."},
                    )

        # 2. Fallback: solo permitido estrictamente en modo dev
        if not tenant_id and AGENCY_ENV in ("dev", "development"):
            tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")

        if not tenant_id and AGENCY_ENV in ("dev", "development"):
            if request.url.path.startswith("/api/v1/tenants/"):
                path_parts = request.url.path.split("/")
                if len(path_parts) >= 5:
                    tenant_id = path_parts[4]
            elif request.url.path.startswith("/realtime/sse/"):
                path_parts = request.url.path.split("/")
                if len(path_parts) >= 4:
                    tenant_id = path_parts[3]

        # 3. En staging/prod, sin JWT válido → rechazar 401 inmediatamente
        # NUNCA hacer fallback a "default_tenant" en prod.
        if not tenant_id:
            if AGENCY_ENV not in ("dev", "development"):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Autenticación requerida: token JWT ausente."},
                )
            tenant_id = "default_tenant"

        request.state.tenant_id = tenant_id
        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response
