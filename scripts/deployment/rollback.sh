#!/usr/bin/env bash
# Detection API - Rollback Script
# Usage: ./rollback.sh <environment> [revision]
#
# If no revision specified, rolls back to the previous release.

set -euo pipefail

ENVIRONMENT="${1:?Usage: rollback.sh <environment> [revision]}"
REVISION="${2:-}"
NAMESPACE="${ENVIRONMENT}"
HELM_RELEASE="detection-api-${ENVIRONMENT}"
TIMEOUT="300s"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }

log_info "=========================================="
log_info "Detection API ROLLBACK"
log_info "Environment: ${ENVIRONMENT}"
log_info "=========================================="

# Record current state
log_info "Current deployment state:"
CURRENT_IMAGE=$(kubectl get deployment "${HELM_RELEASE}" -n "${NAMESPACE}" \
    -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "unknown")
log_info "  Current image: ${CURRENT_IMAGE}"

# Show history
log_info "Helm release history:"
helm history "${HELM_RELEASE}" -n "${NAMESPACE}" --max 5 2>/dev/null || \
    log_warn "No Helm history available"

# Execute rollback
if [ -n "${REVISION}" ]; then
    log_info "Rolling back to revision: ${REVISION}"
    helm rollback "${HELM_RELEASE}" "${REVISION}" -n "${NAMESPACE}" --wait --timeout "${TIMEOUT}"
else
    log_info "Rolling back to previous revision..."
    helm rollback "${HELM_RELEASE}" -n "${NAMESPACE}" --wait --timeout "${TIMEOUT}"
fi

# Verify rollback
kubectl rollout status deployment/"${HELM_RELEASE}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"

NEW_IMAGE=$(kubectl get deployment "${HELM_RELEASE}" -n "${NAMESPACE}" \
    -o jsonpath='{.spec.template.spec.containers[0].image}')
log_info "Rolled back to image: ${NEW_IMAGE}"

# Health check
POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
    --no-headers -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "${POD_NAME}" ]; then
    HEALTH=$(kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -- \
        curl -sf http://localhost:8000/api/v1/health 2>/dev/null || echo "FAILED")
    if echo "${HEALTH}" | grep -q "running"; then
        log_info "Post-rollback health check: PASSED"
    else
        log_error "Post-rollback health check: FAILED"
        exit 1
    fi
fi

log_info "=========================================="
log_info "ROLLBACK COMPLETE"
log_info "  From: ${CURRENT_IMAGE}"
log_info "  To:   ${NEW_IMAGE}"
log_info "=========================================="
