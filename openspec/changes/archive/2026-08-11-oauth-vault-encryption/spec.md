# OpenSpec Spec: OAuth Token Vault Encryption & Request Validation

## Requirements & Scenarios

### REQ-OVE-01: Cifrado Simétrico de Tokens (AES-256 / Fernet)
- **Scenario 1:** `encrypt_token("plain_oauth_token")` devuelve un ciphertext seguro codificado en Base64url que no revela el token original.
- **Scenario 2:** `decrypt_token(ciphertext)` recupera exactamente el string original `plain_oauth_token`.
- **Scenario 3:** `encrypt_token("")` o `encrypt_token(None)` retorna `""` o `None` sin lanzar excepciones indeseadas.

### REQ-OVE-02: Validación de Tokens en Payload HTTP (RELIABILITY-005)
- **Scenario 1:** Enviar un `GraphRunRequest` con `ig_access_token="   "` (solo espacios) o tokens con caracteres de control genera un error de validación HTTP `422 Unprocessable Entity`.
- **Scenario 2:** Enviar un token válido (`EAAG...` o `token_dev`) pasa la validación e inicia la ejecución del grafo.
