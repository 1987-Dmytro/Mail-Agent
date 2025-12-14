#!/bin/bash
#
# Database Backup Script for Oracle Autonomous Database
# Creates automated backups and manages retention
#
# Usage: bash backup-database.sh [staging|production]
#

set -e

ENV=${1:-staging}
BACKUP_DIR="$HOME/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=14

echo "=================================================="
echo "  Database Backup - $ENV"
echo "  Date: $(date)"
echo "=================================================="

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load database URL from .env
cd ~/Mail-Agent/backend
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Extract database connection details
source .env

if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL not found in .env"
    exit 1
fi

BACKUP_FILE="$BACKUP_DIR/mailagent_${ENV}_${DATE}.sql"

echo "Creating backup: $BACKUP_FILE"

# For Oracle Autonomous Database, use Docker to run pg_dump
docker exec -i $(docker ps -qf "name=db") pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --verbose \
    --no-owner \
    --no-acl \
    > "$BACKUP_FILE" 2>/dev/null

# Compress backup
echo "Compressing backup..."
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"

# Clean up old backups (keep last 14 days)
echo "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "mailagent_${ENV}_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List recent backups
echo ""
echo "Recent backups:"
ls -lh "$BACKUP_DIR"/mailagent_${ENV}_*.sql.gz 2>/dev/null | tail -5 || echo "No backups found"

echo ""
echo "Backup completed successfully!"
