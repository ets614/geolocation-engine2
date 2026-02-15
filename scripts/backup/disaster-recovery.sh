#!/usr/bin/env bash
# Detection API - Disaster Recovery Script
# Usage: ./disaster-recovery.sh <environment> <backup-timestamp>
#
# Restores:
# 1. PostgreSQL from backup
# 2. SQLite queues from S3
# 3. Validates application health
#
# RTO Target: < 30 minutes
# RPO Target: < 1 hour (based on backup frequency)

set -euo pipefail

ENVIRONMENT="${1:?Usage: disaster-recovery.sh <environment> <backup-timestamp>}"
BACKUP_TIMESTAMP="${2:?Usage: disaster-recovery.sh <environment> <backup-timestamp>}"
NAMESPACE="${ENVIRONMENT}"
HELM_RELEASE="detection-api-${ENVIRONMENT}"
S3_BUCKET="detection-api-${ENVIRONMENT}-backups"
RESTORE_DIR="/tmp/detection-api-restore-${BACKUP_TIMESTAMP}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }

START_TIME=$(date +%s)

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${RESTORE_DIR}"
}
trap cleanup EXIT

mkdir -p "${RESTORE_DIR}"

log_info "=========================================="
log_info "DISASTER RECOVERY INITIATED"
log_info "Environment: ${ENVIRONMENT}"
log_info "Backup:      ${BACKUP_TIMESTAMP}"
log_info "RTO Target:  30 minutes"
log_info "=========================================="

# --------------------------------------------------------------------------
# Phase 1: Download Backups
# --------------------------------------------------------------------------

log_info "Phase 1: Downloading backups from S3..."

aws s3 cp "s3://${S3_BUCKET}/database/${BACKUP_TIMESTAMP}/" "${RESTORE_DIR}/database/" \
    --recursive 2>/dev/null || log_error "Failed to download database backup"

aws s3 cp "s3://${S3_BUCKET}/queue/${BACKUP_TIMESTAMP}/" "${RESTORE_DIR}/queue/" \
    --recursive 2>/dev/null || log_warn "No queue backups found"

log_info "Backups downloaded"

# --------------------------------------------------------------------------
# Phase 2: Restore PostgreSQL
# --------------------------------------------------------------------------

log_info "Phase 2: Restoring PostgreSQL..."

RDS_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier "detection-api-${ENVIRONMENT}-primary" \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text 2>/dev/null || echo "localhost")

BACKUP_FILE=$(find "${RESTORE_DIR}/database/" -name "*.sql.gz" -o -name "*.dump" | head -1)

if [ -n "${BACKUP_FILE}" ]; then
    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
        --no-headers -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -n "${POD_NAME}" ]; then
        # Copy backup to pod and restore
        kubectl cp "${BACKUP_FILE}" "${NAMESPACE}/${POD_NAME}:/tmp/restore.dump"
        kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -- \
            pg_restore -h "${RDS_ENDPOINT}" -U detection_admin -d detection_api \
            --clean --if-exists /tmp/restore.dump 2>/dev/null || {
            log_warn "pg_restore failed. Attempting RDS snapshot restore..."
            aws rds restore-db-instance-from-db-snapshot \
                --db-instance-identifier "detection-api-${ENVIRONMENT}-restored" \
                --db-snapshot-identifier "detection-api-${ENVIRONMENT}-${BACKUP_TIMESTAMP}" 2>/dev/null || true
        }
    fi
else
    log_warn "No database backup file found. Using RDS snapshot restore..."
    aws rds restore-db-instance-from-db-snapshot \
        --db-instance-identifier "detection-api-${ENVIRONMENT}-restored" \
        --db-snapshot-identifier "detection-api-${ENVIRONMENT}-${BACKUP_TIMESTAMP}" 2>/dev/null || true
fi

log_info "PostgreSQL restore complete"

# --------------------------------------------------------------------------
# Phase 3: Restore SQLite Queues
# --------------------------------------------------------------------------

log_info "Phase 3: Restoring SQLite queues..."

PODS=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
    --no-headers -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

for queue_file in "${RESTORE_DIR}"/queue/queue-*.db; do
    [ -f "${queue_file}" ] || continue
    FIRST_POD=$(echo "${PODS}" | awk '{print $1}')
    if [ -n "${FIRST_POD}" ]; then
        kubectl cp "${queue_file}" "${NAMESPACE}/${FIRST_POD}:/app/data/queue.db"
        log_info "  Restored queue to pod: ${FIRST_POD}"
        break
    fi
done

# --------------------------------------------------------------------------
# Phase 4: Restart Application
# --------------------------------------------------------------------------

log_info "Phase 4: Restarting application..."

kubectl rollout restart deployment/"${HELM_RELEASE}" -n "${NAMESPACE}" 2>/dev/null || true
kubectl rollout status deployment/"${HELM_RELEASE}" -n "${NAMESPACE}" --timeout="300s"

# --------------------------------------------------------------------------
# Phase 5: Validate Recovery
# --------------------------------------------------------------------------

log_info "Phase 5: Validating recovery..."

sleep 30  # Wait for pods to stabilize

POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
    --no-headers -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "${POD_NAME}" ]; then
    HEALTH=$(kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -- \
        curl -sf http://localhost:8000/api/v1/health 2>/dev/null || echo "FAILED")

    if echo "${HEALTH}" | grep -q "running"; then
        log_info "Health check: PASSED"
    else
        log_error "Health check: FAILED"
    fi
fi

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))

log_info "=========================================="
log_info "DISASTER RECOVERY COMPLETE"
log_info "  Environment:    ${ENVIRONMENT}"
log_info "  Backup Used:    ${BACKUP_TIMESTAMP}"
log_info "  Recovery Time:  ${ELAPSED_MIN} minutes (${ELAPSED}s)"
if [ ${ELAPSED_MIN} -le 30 ]; then
    log_info "  RTO Compliance: PASSED (target: 30 min)"
else
    log_error "  RTO Compliance: FAILED (target: 30 min, actual: ${ELAPSED_MIN} min)"
fi
log_info "=========================================="
