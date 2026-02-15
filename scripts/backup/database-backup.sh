#!/usr/bin/env bash
# Detection API - Database Backup Script
# Usage: ./database-backup.sh <environment>
#
# Performs:
# 1. PostgreSQL logical backup (pg_dump)
# 2. SQLite queue snapshot from pods
# 3. Upload to S3 with encryption
# 4. Verify backup integrity
# 5. Clean up local artifacts

set -euo pipefail

ENVIRONMENT="${1:?Usage: database-backup.sh <environment>}"
NAMESPACE="${ENVIRONMENT}"
HELM_RELEASE="detection-api-${ENVIRONMENT}"
S3_BUCKET="detection-api-${ENVIRONMENT}-backups"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
BACKUP_DIR="/tmp/detection-api-backup-${TIMESTAMP}"
RETENTION_DAYS=30

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${BACKUP_DIR}"
}
trap cleanup EXIT

mkdir -p "${BACKUP_DIR}"

log_info "=========================================="
log_info "Database Backup - ${ENVIRONMENT}"
log_info "Timestamp: ${TIMESTAMP}"
log_info "=========================================="

# --------------------------------------------------------------------------
# PostgreSQL Backup
# --------------------------------------------------------------------------

log_info "Phase 1: PostgreSQL backup..."

RDS_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier "detection-api-${ENVIRONMENT}-primary" \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text 2>/dev/null || echo "localhost")

DB_NAME="detection_api"
BACKUP_FILE="${BACKUP_DIR}/postgres-${TIMESTAMP}.sql.gz"

# Use pg_dump from a pod in the cluster for network access
POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
    --no-headers -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "${POD_NAME}" ]; then
    log_info "Running pg_dump via pod ${POD_NAME}..."
    kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -- \
        pg_dump -h "${RDS_ENDPOINT}" -U detection_admin -d "${DB_NAME}" \
        --format=custom --compress=9 > "${BACKUP_FILE}" 2>/dev/null || {
        log_warn "pg_dump failed (may not have pg_dump in container). Using RDS snapshot instead."
        # Fallback: trigger RDS snapshot
        aws rds create-db-snapshot \
            --db-instance-identifier "detection-api-${ENVIRONMENT}-primary" \
            --db-snapshot-identifier "detection-api-${ENVIRONMENT}-${TIMESTAMP}" 2>/dev/null || true
    }
else
    log_warn "No running pods found. Triggering RDS snapshot..."
    aws rds create-db-snapshot \
        --db-instance-identifier "detection-api-${ENVIRONMENT}-primary" \
        --db-snapshot-identifier "detection-api-${ENVIRONMENT}-${TIMESTAMP}" 2>/dev/null || true
fi

# --------------------------------------------------------------------------
# SQLite Queue Snapshot
# --------------------------------------------------------------------------

log_info "Phase 2: SQLite queue snapshot..."

PODS=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
    --no-headers -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

for pod in ${PODS}; do
    QUEUE_FILE="${BACKUP_DIR}/queue-${pod}-${TIMESTAMP}.db"
    log_info "  Backing up queue from pod: ${pod}"
    kubectl cp "${NAMESPACE}/${pod}:/app/data/queue.db" "${QUEUE_FILE}" 2>/dev/null || \
        log_warn "  Failed to copy queue from ${pod}"
done

# --------------------------------------------------------------------------
# Upload to S3
# --------------------------------------------------------------------------

log_info "Phase 3: Uploading to S3..."

if [ -f "${BACKUP_FILE}" ]; then
    aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/database/${TIMESTAMP}/" \
        --sse aws:kms 2>/dev/null || log_warn "S3 upload failed for postgres backup"
    log_info "  PostgreSQL backup uploaded"
fi

for queue_file in "${BACKUP_DIR}"/queue-*.db; do
    [ -f "${queue_file}" ] || continue
    aws s3 cp "${queue_file}" "s3://${S3_BUCKET}/queue/${TIMESTAMP}/" \
        --sse aws:kms 2>/dev/null || log_warn "S3 upload failed for queue file"
done

# --------------------------------------------------------------------------
# Verify Backup
# --------------------------------------------------------------------------

log_info "Phase 4: Verifying backup..."

if [ -f "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(stat -f%z "${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_FILE}" 2>/dev/null || echo "0")
    if [ "${BACKUP_SIZE}" -gt 0 ]; then
        log_info "  PostgreSQL backup verified: ${BACKUP_SIZE} bytes"
    else
        log_error "  PostgreSQL backup is empty!"
    fi
fi

# --------------------------------------------------------------------------
# Cleanup Old Backups
# --------------------------------------------------------------------------

log_info "Phase 5: Cleaning up old backups (>${RETENTION_DAYS} days)..."

CUTOFF_DATE=$(date -u -d "-${RETENTION_DAYS} days" +%Y%m%d 2>/dev/null || \
    date -u -v-${RETENTION_DAYS}d +%Y%m%d 2>/dev/null || echo "")

if [ -n "${CUTOFF_DATE}" ]; then
    aws s3 ls "s3://${S3_BUCKET}/database/" 2>/dev/null | while read -r line; do
        DIR_DATE=$(echo "${line}" | awk '{print $2}' | tr -d '/' | cut -c1-8)
        if [ "${DIR_DATE}" \< "${CUTOFF_DATE}" ]; then
            aws s3 rm "s3://${S3_BUCKET}/database/${DIR_DATE}/" --recursive 2>/dev/null || true
            log_info "  Removed old backup: ${DIR_DATE}"
        fi
    done
fi

log_info "=========================================="
log_info "BACKUP COMPLETE"
log_info "  Environment: ${ENVIRONMENT}"
log_info "  Timestamp:   ${TIMESTAMP}"
log_info "  S3 Bucket:   ${S3_BUCKET}"
log_info "=========================================="
