#!/bin/bash

# Script de backup PostgreSQL vers cloud (rclone)
# Usage: ./backup.sh

set -euo pipefail

BACKUP_DIR="/tmp/marstek-backups"
DB_NAME="marstek_db"
DB_USER="marstek"
CONTAINER_NAME="marstek-automation-postgres-1"
RCLONE_REMOTE="gdrive"
RCLONE_PATH="marstek-backups"
RETENTION_DAYS=30

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/marstek_backup_$(date +%Y%m%d_%H%M%S).sql"
BACKUP_FILE_COMPRESSED="${BACKUP_FILE}.gz"

log "Démarrage du backup de la base de données ${DB_NAME}"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: Le conteneur PostgreSQL n'est pas en cours d'exécution"
    exit 1
fi

log "Création du dump PostgreSQL..."
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists > "${BACKUP_FILE}"

log "Compression du backup..."
gzip -f "${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_FILE_COMPRESSED}" | cut -f1)
log "Taille du backup: ${BACKUP_SIZE}"

if command -v rclone &> /dev/null; then
    if rclone listremotes | grep -q "^${RCLONE_REMOTE}:$"; then
        log "Upload du backup vers ${RCLONE_REMOTE}:${RCLONE_PATH}..."
        rclone copy "${BACKUP_FILE_COMPRESSED}" "${RCLONE_REMOTE}:${RCLONE_PATH}/" --progress
    fi
fi

log "Nettoyage des backups locaux de plus de ${RETENTION_DAYS} jours..."
find "${BACKUP_DIR}" -name "marstek_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

log "Backup terminé avec succès"
