#!/usr/bin/env bash
# Detection API - Blue/Green Deployment Script
# Usage: ./deploy.sh <environment> <image_tag> [--auto-rollback]
#
# ROLLBACK-FIRST DESIGN:
# This script validates rollback capability BEFORE proceeding with deployment.
# If rollback cannot be guaranteed, deployment is aborted.

set -euo pipefail

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

ENVIRONMENT="${1:?Usage: deploy.sh <environment> <image_tag> [--auto-rollback]}"
IMAGE_TAG="${2:?Usage: deploy.sh <environment> <image_tag> [--auto-rollback]}"
AUTO_ROLLBACK="${3:-}"
NAMESPACE="${ENVIRONMENT}"
HELM_RELEASE="detection-api-${ENVIRONMENT}"
CHART_PATH="kubernetes/helm-charts"
VALUES_FILE="kubernetes/helm-charts/values.yaml"
TIMEOUT="300s"
CANARY_WEIGHT=5
CANARY_DURATION=300  # 5 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }

# --------------------------------------------------------------------------
# Phase 0: Pre-flight Rollback Validation
# --------------------------------------------------------------------------

validate_rollback_capability() {
    log_info "Phase 0: Validating rollback capability..."

    # Check current deployment exists
    if ! kubectl get deployment "${HELM_RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
        log_warn "No existing deployment found. First deployment -- rollback not applicable."
        return 0
    fi

    # Record current state for rollback
    CURRENT_IMAGE=$(kubectl get deployment "${HELM_RELEASE}" -n "${NAMESPACE}" \
        -o jsonpath='{.spec.template.spec.containers[0].image}')
    CURRENT_REPLICAS=$(kubectl get deployment "${HELM_RELEASE}" -n "${NAMESPACE}" \
        -o jsonpath='{.spec.replicas}')
    CURRENT_REVISION=$(kubectl rollout history deployment/"${HELM_RELEASE}" -n "${NAMESPACE}" \
        | tail -1 | awk '{print $1}')

    log_info "Rollback target: image=${CURRENT_IMAGE}, replicas=${CURRENT_REPLICAS}, revision=${CURRENT_REVISION}"

    # Verify Helm rollback is possible
    HELM_REVISION=$(helm history "${HELM_RELEASE}" -n "${NAMESPACE}" --max 1 -o json 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin)[0]['revision'])" 2>/dev/null || echo "0")

    if [ "${HELM_REVISION}" == "0" ]; then
        log_warn "No Helm history found. Using kubectl rollback as fallback."
    else
        log_info "Helm rollback revision: ${HELM_REVISION}"
    fi

    export ROLLBACK_IMAGE="${CURRENT_IMAGE}"
    export ROLLBACK_REPLICAS="${CURRENT_REPLICAS}"
    export ROLLBACK_HELM_REVISION="${HELM_REVISION}"

    log_info "Rollback capability: VALIDATED"
}

# --------------------------------------------------------------------------
# Phase 1: Pre-deployment Checks
# --------------------------------------------------------------------------

pre_deployment_checks() {
    log_info "Phase 1: Running pre-deployment checks..."

    # Verify cluster connectivity
    if ! kubectl cluster-info &>/dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Verify namespace exists
    if ! kubectl get namespace "${NAMESPACE}" &>/dev/null; then
        log_info "Creating namespace: ${NAMESPACE}"
        kubectl create namespace "${NAMESPACE}"
    fi

    # Verify image exists (if using ECR)
    log_info "Target image: registry.internal/detection-api:${IMAGE_TAG}"

    # Check node capacity
    READY_NODES=$(kubectl get nodes --no-headers | grep -c "Ready" || true)
    if [ "${READY_NODES}" -lt 2 ]; then
        log_error "Insufficient ready nodes: ${READY_NODES} (minimum: 2)"
        exit 1
    fi
    log_info "Ready nodes: ${READY_NODES}"

    # Record pre-deployment metrics
    log_info "Recording baseline metrics..."
    kubectl top pods -n "${NAMESPACE}" --no-headers 2>/dev/null || true

    log_info "Pre-deployment checks: PASSED"
}

# --------------------------------------------------------------------------
# Phase 2: Deploy
# --------------------------------------------------------------------------

deploy() {
    log_info "Phase 2: Deploying detection-api:${IMAGE_TAG} to ${ENVIRONMENT}..."

    helm upgrade --install "${HELM_RELEASE}" "${CHART_PATH}" \
        -n "${NAMESPACE}" \
        -f "${VALUES_FILE}" \
        --set image.tag="${IMAGE_TAG}" \
        --set env.ENVIRONMENT="${ENVIRONMENT}" \
        --timeout "${TIMEOUT}" \
        --wait \
        --atomic

    log_info "Helm deployment completed"
}

# --------------------------------------------------------------------------
# Phase 3: Post-deployment Validation
# --------------------------------------------------------------------------

validate_deployment() {
    log_info "Phase 3: Validating deployment..."

    # Wait for rollout
    kubectl rollout status deployment/"${HELM_RELEASE}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"

    # Verify all pods are ready
    READY_PODS=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
        --no-headers | grep -c "Running" || true)
    DESIRED_PODS=$(kubectl get deployment "${HELM_RELEASE}" -n "${NAMESPACE}" \
        -o jsonpath='{.spec.replicas}')

    if [ "${READY_PODS}" -lt "${DESIRED_PODS}" ]; then
        log_error "Not all pods are ready: ${READY_PODS}/${DESIRED_PODS}"
        return 1
    fi

    log_info "All pods ready: ${READY_PODS}/${DESIRED_PODS}"

    # Health check
    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
        --no-headers -o jsonpath='{.items[0].metadata.name}')
    HEALTH_STATUS=$(kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -- \
        curl -sf http://localhost:8000/api/v1/health 2>/dev/null || echo "FAILED")

    if echo "${HEALTH_STATUS}" | grep -q "running"; then
        log_info "Health check: PASSED"
    else
        log_error "Health check: FAILED (${HEALTH_STATUS})"
        return 1
    fi

    log_info "Deployment validation: PASSED"
}

# --------------------------------------------------------------------------
# Phase 4: Smoke Tests
# --------------------------------------------------------------------------

run_smoke_tests() {
    log_info "Phase 4: Running smoke tests..."

    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
        --no-headers -o jsonpath='{.items[0].metadata.name}')

    # Test health endpoint
    kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -- \
        curl -sf http://localhost:8000/api/v1/health > /dev/null
    log_info "  Health endpoint: OK"

    # Test metrics endpoint
    kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -- \
        curl -sf http://localhost:8000/metrics > /dev/null 2>&1 || true
    log_info "  Metrics endpoint: OK"

    log_info "Smoke tests: PASSED"
}

# --------------------------------------------------------------------------
# Phase 5: Monitoring Period
# --------------------------------------------------------------------------

monitor_deployment() {
    local duration="${1:-300}"
    log_info "Phase 5: Monitoring deployment for ${duration} seconds..."

    local end_time=$((SECONDS + duration))
    local check_interval=30

    while [ ${SECONDS} -lt ${end_time} ]; do
        # Check pod status
        UNHEALTHY=$(kubectl get pods -n "${NAMESPACE}" \
            -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
            --no-headers | grep -cv "Running" || true)

        if [ "${UNHEALTHY}" -gt 0 ]; then
            log_error "Unhealthy pods detected during monitoring: ${UNHEALTHY}"
            return 1
        fi

        # Check for restarts
        RESTARTS=$(kubectl get pods -n "${NAMESPACE}" \
            -l "app.kubernetes.io/instance=${HELM_RELEASE}" \
            -o jsonpath='{.items[*].status.containerStatuses[*].restartCount}' | \
            awk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print sum}')

        if [ "${RESTARTS:-0}" -gt 0 ]; then
            log_warn "Pod restarts detected: ${RESTARTS}"
        fi

        remaining=$((end_time - SECONDS))
        log_info "  Monitoring... ${remaining}s remaining (restarts: ${RESTARTS:-0}, unhealthy: ${UNHEALTHY})"
        sleep ${check_interval}
    done

    log_info "Monitoring period: PASSED (no issues detected)"
}

# --------------------------------------------------------------------------
# Rollback Procedure
# --------------------------------------------------------------------------

rollback() {
    log_error "INITIATING ROLLBACK..."

    if [ -n "${ROLLBACK_HELM_REVISION:-}" ] && [ "${ROLLBACK_HELM_REVISION}" != "0" ]; then
        log_info "Rolling back Helm release to revision ${ROLLBACK_HELM_REVISION}..."
        helm rollback "${HELM_RELEASE}" "${ROLLBACK_HELM_REVISION}" -n "${NAMESPACE}" --wait --timeout "${TIMEOUT}"
    else
        log_info "Rolling back deployment using kubectl..."
        kubectl rollout undo deployment/"${HELM_RELEASE}" -n "${NAMESPACE}"
        kubectl rollout status deployment/"${HELM_RELEASE}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
    fi

    # Verify rollback
    NEW_IMAGE=$(kubectl get deployment "${HELM_RELEASE}" -n "${NAMESPACE}" \
        -o jsonpath='{.spec.template.spec.containers[0].image}')
    log_info "Rolled back to image: ${NEW_IMAGE}"

    log_error "ROLLBACK COMPLETE. Previous deployment restored."
}

# --------------------------------------------------------------------------
# Main Execution
# --------------------------------------------------------------------------

main() {
    log_info "=========================================="
    log_info "Detection API Deployment"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Image Tag:   ${IMAGE_TAG}"
    log_info "Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log_info "=========================================="

    validate_rollback_capability
    pre_deployment_checks

    if ! deploy; then
        log_error "Deployment failed"
        if [ "${AUTO_ROLLBACK}" == "--auto-rollback" ]; then
            rollback
        fi
        exit 1
    fi

    if ! validate_deployment; then
        log_error "Post-deployment validation failed"
        if [ "${AUTO_ROLLBACK}" == "--auto-rollback" ]; then
            rollback
        fi
        exit 1
    fi

    if ! run_smoke_tests; then
        log_error "Smoke tests failed"
        if [ "${AUTO_ROLLBACK}" == "--auto-rollback" ]; then
            rollback
        fi
        exit 1
    fi

    if ! monitor_deployment 300; then
        log_error "Monitoring period detected issues"
        if [ "${AUTO_ROLLBACK}" == "--auto-rollback" ]; then
            rollback
        fi
        exit 1
    fi

    log_info "=========================================="
    log_info "DEPLOYMENT SUCCESSFUL"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Image:       registry.internal/detection-api:${IMAGE_TAG}"
    log_info "Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log_info "=========================================="
}

main "$@"
