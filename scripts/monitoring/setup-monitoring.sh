#!/usr/bin/env bash
# Detection API - Monitoring Stack Setup
# Installs: Prometheus Operator, Grafana, Loki, Alertmanager
# Usage: ./setup-monitoring.sh <environment>

set -euo pipefail

ENVIRONMENT="${1:?Usage: setup-monitoring.sh <environment>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MONITORING_DIR="${PROJECT_ROOT}/kubernetes/monitoring"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"; }

log_info "=========================================="
log_info "Monitoring Stack Setup - ${ENVIRONMENT}"
log_info "=========================================="

# --------------------------------------------------------------------------
# Create monitoring namespace
# --------------------------------------------------------------------------

log_info "Creating monitoring namespace..."
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace monitoring name=monitoring --overwrite

# --------------------------------------------------------------------------
# Add Helm repositories
# --------------------------------------------------------------------------

log_info "Adding Helm repositories..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# --------------------------------------------------------------------------
# Install Prometheus Operator + Grafana + Alertmanager
# --------------------------------------------------------------------------

log_info "Installing kube-prometheus-stack..."
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
    -n monitoring \
    -f "${MONITORING_DIR}/prometheus/prometheus-values.yaml" \
    --wait \
    --timeout 600s

# --------------------------------------------------------------------------
# Install Loki Stack
# --------------------------------------------------------------------------

log_info "Installing Loki stack..."
helm upgrade --install loki grafana/loki-stack \
    -n monitoring \
    -f "${MONITORING_DIR}/loki/loki-values.yaml" \
    --wait \
    --timeout 300s

# --------------------------------------------------------------------------
# Apply Alerting Rules
# --------------------------------------------------------------------------

log_info "Applying alerting rules..."
kubectl apply -f "${MONITORING_DIR}/prometheus/alerting-rules.yaml"

# --------------------------------------------------------------------------
# Apply Alertmanager Configuration
# --------------------------------------------------------------------------

log_info "Applying alertmanager configuration..."
kubectl apply -f "${MONITORING_DIR}/alertmanager/alertmanager-config.yaml"

# --------------------------------------------------------------------------
# Import Grafana Dashboards
# --------------------------------------------------------------------------

log_info "Importing Grafana dashboards..."
kubectl create configmap detection-api-dashboard \
    --from-file="${MONITORING_DIR}/grafana/detection-api-dashboard.json" \
    -n monitoring \
    --dry-run=client -o yaml | kubectl apply -f -
kubectl label configmap detection-api-dashboard \
    grafana_dashboard=1 \
    -n monitoring \
    --overwrite

# --------------------------------------------------------------------------
# Verify Installation
# --------------------------------------------------------------------------

log_info "Verifying monitoring stack..."

log_info "  Prometheus pods:"
kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus --no-headers 2>/dev/null || true

log_info "  Grafana pods:"
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana --no-headers 2>/dev/null || true

log_info "  Loki pods:"
kubectl get pods -n monitoring -l app=loki --no-headers 2>/dev/null || true

log_info "  Alertmanager pods:"
kubectl get pods -n monitoring -l app.kubernetes.io/name=alertmanager --no-headers 2>/dev/null || true

log_info "=========================================="
log_info "MONITORING SETUP COMPLETE"
log_info "  Grafana:      kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring"
log_info "  Prometheus:    kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090 -n monitoring"
log_info "  Alertmanager:  kubectl port-forward svc/prometheus-kube-prometheus-alertmanager 9093 -n monitoring"
log_info "=========================================="
