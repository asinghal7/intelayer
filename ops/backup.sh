#!/usr/bin/env bash
set -euo pipefail
: "${DB_URL:?Set DB_URL in environment}"
STAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p ops/backups
pg_dump "$DB_URL" > "ops/backups/intelayer_${STAMP}.sql"
find ops/backups -type f -mtime +14 -delete
echo "Backup complete: ops/backups/intelayer_${STAMP}.sql"

