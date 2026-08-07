#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-viralsync}"
POSTGRES_DB="${POSTGRES_DB:-viralsync_db}"
RETENTION_DAYS=7

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/postgres_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Iniciando respaldo de PostgreSQL database '${POSTGRES_DB}' en '${BACKUP_FILE}'..."

PGPASSWORD="${POSTGRES_PASSWORD:-viralsync_pass}" pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_FILE}"

echo "[$(date)] Respaldo completado exitosamente: ${BACKUP_FILE}"

echo "[$(date)] Limpiando respaldos antiguos (más de ${RETENTION_DAYS} días)..."
find "${BACKUP_DIR}" -type f -name "postgres_${POSTGRES_DB}_*.sql.gz" -mtime +${RETENTION_DAYS} -delete || true

echo "[$(date)] Proceso de respaldo y rotación finalizado."
