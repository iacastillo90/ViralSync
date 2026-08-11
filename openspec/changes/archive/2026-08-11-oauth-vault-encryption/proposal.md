# OpenSpec Proposal: OAuth Token Vault Encryption & Request Validation (RELIABILITY-005)

- **Change ID:** `oauth-vault-encryption`
- **Scope:** Encriptación de tokens OAuth de redes sociales en repositorios/BD con AES-256-GCM / Fernet y validación estricta en payloads de API (`GraphRunRequest`).

## Problem Statement
1. **Tokens OAuth en Plano (Riesgo de Seguridad):** Los tokens de Instagram, TikTok y YouTube se procesan en el estado del grafo y en futuras extensiones se persistirán. Sin un mecanismo de cifrado simétrico robusto, la fuga de una base de datos expondría tokens de acceso con permisos de publicación.
2. **Falta de Validación de Tokens (RELIABILITY-005):** El endpoint `/graph/run` (`graph_execution.py`) aceptaba valores arbitrarios o vacíos en `ig_access_token`, `tiktok_access_token` y `youtube_access_token`, propagando strings malformados que hacían fallar los nodos de publicación en etapas tardías de la ejecución.

## Proposed Solution
1. **Módulo de Cifrado (`backend/security/crypto.py`):** Crear funciones `encrypt_token(token: str) -> str` y `decrypt_token(cipher_text: str) -> str` utilizando AES-256 / Fernet derivado de la variable de entorno `OAUTH_ENCRYPTION_KEY` (con fallback a clave derivada de `JWT_SECRET_KEY` en dev).
2. **Validación Pydantic en Router:** Inyectar validadores pydantic `@field_validator` en `GraphRunRequest` para garantizar que cuando se provea un token, cumpla con los requisitos mínimos de formato (no vacío, sin espacios, longitud mínima).
