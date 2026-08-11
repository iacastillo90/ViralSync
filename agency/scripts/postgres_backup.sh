#!/usr/bin/env bash
# postgres_backup.sh
# Script de respaldos automáticos de PostgreSQL con compresión y rotación.

set -eo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/viralsync_db_${TIMESTAMP}.sql.gz"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Iniciando respaldo de PostgreSQL a ${BACKUP_FILE}..."
PGPASSWORD="${POSTGRES_PASSWORD:-prod_pass}" pg_dump \
  -h "${POSTGRES_HOST:-postgres}" \
  -U "${POSTGRES_USER:-viralsync}" \
  -d "${POSTGRES_DB:-viralsync_db}" \
  | gzip > "${BACKUP_FILE}"

echo "[$(date)] Respaldo completado exitosamente. Eliminando backups con más de ${RETENTION_DAYS} días..."
find "${BACKUP_DIR}" -type f -name "viralsync_db_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "[$(date)] Proceso de respaldo finalizado."
