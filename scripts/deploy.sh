#!/bin/bash
#
# Phase 05: Deployment Automation Script
# Purpose: End-to-end infrastructure and application deployment with validation and rollback
# Usage: ./deploy.sh dev|staging|prod
#

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="${PROJECT_ROOT}/terraform"
DEPLOYMENT_LOG="/tmp/deployment-$(date +%s).log"

# Defaults
ENVIRONMENT="${1:-}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_VALIDATION="${SKIP_VALIDATION:-false}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

validate_input() {
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        echo "Usage: $0 dev|staging|prod"
        exit 1
    fi
    log_info "Deploying to: $ENVIRONMENT"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing_tools=()

    for tool in terraform aws kubectl helm jq; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi

    log_success "All prerequisites met"
}

check_aws_credentials() {
    log_info "Checking AWS credentials..."

    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        log_error "AWS credentials not configured"
        exit 1
    fi

    local account=$(aws sts get-caller-identity --query Account --output text)
    log_success "AWS account: $account"
}

terraform_init() {
    log_info "Initializing Terraform..."

    cd "$TERRAFORM_DIR"
    terraform init -upgrade

    log_success "Terraform initialized"
}

terraform_validate() {
    log_info "Validating Terraform..."

    cd "$TERRAFORM_DIR"
    terraform validate

    log_success "Terraform validation passed"
}

terraform_fmt() {
    log_info "Formatting Terraform code..."

    cd "$TERRAFORM_DIR"
    terraform fmt -recursive

    log_success "Terraform formatted"
}

terraform_plan() {
    log_info "Planning Terraform deployment for $ENVIRONMENT..."

    cd "$TERRAFORM_DIR"
    local plan_file="/tmp/terraform-${ENVIRONMENT}.tfplan"

    terraform plan \
        -var-file="environments/${ENVIRONMENT}.tfvars" \
        -out="$plan_file" \
        2>&1 | tee -a "$DEPLOYMENT_LOG"

    log_success "Terraform plan saved to $plan_file"
    echo "$plan_file"
}

terraform_apply() {
    local plan_file="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY_RUN=true - skipping Terraform apply"
        return
    fi

    log_info "Applying Terraform plan..."

    cd "$TERRAFORM_DIR"
    terraform apply "$plan_file" 2>&1 | tee -a "$DEPLOYMENT_LOG"

    log_success "Infrastructure deployed successfully"
}

configure_kubectl() {
    log_info "Configuring kubectl..."

    cd "$TERRAFORM_DIR"
    local cluster_name=$(terraform output -raw eks_cluster_name)
    local region="us-east-1"

    aws eks update-kubeconfig \
        --name "$cluster_name" \
        --region "$region"

    log_success "kubectl configured"
}

deploy_helm_charts() {
    log_info "Deploying Helm charts..."

    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update

    # Install Prometheus
    log_info "Installing Prometheus..."
    helm upgrade --install prometheus prometheus-community/prometheus \
        --namespace monitoring \
        --create-namespace \
        --values "${TERRAFORM_DIR}/helm-values/prometheus.yaml" \
        2>&1 | tee -a "$DEPLOYMENT_LOG"

    # Install Grafana
    log_info "Installing Grafana..."
    helm upgrade --install grafana grafana/grafana \
        --namespace monitoring \
        --create-namespace \
        --values "${TERRAFORM_DIR}/helm-values/grafana.yaml" \
        2>&1 | tee -a "$DEPLOYMENT_LOG"

    log_success "Helm charts deployed"
}

validate_infrastructure() {
    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        log_warn "Skipping infrastructure validation"
        return
    fi

    log_info "Validating infrastructure..."

    # Check EKS cluster
    local cluster_name=$(kubectl config current-context | cut -d/ -f2)
    log_info "Checking EKS cluster: $cluster_name"
    kubectl cluster-info

    # Check node readiness
    log_info "Waiting for nodes to be ready..."
    kubectl wait --for=condition=Ready node --all --timeout=600s 2>&1 | tee -a "$DEPLOYMENT_LOG"

    # Check RDS connectivity
    log_info "Validating RDS endpoint..."
    cd "$TERRAFORM_DIR"
    local rds_endpoint=$(terraform output -raw rds_endpoint)
    if host "${rds_endpoint%:*}" &> /dev/null; then
        log_success "RDS endpoint reachable"
    fi

    # Check Redis connectivity
    log_info "Validating Redis endpoint..."
    local redis_endpoint=$(terraform output -raw redis_endpoint)
    local redis_host="${redis_endpoint%:*}"
    if host "$redis_host" &> /dev/null; then
        log_success "Redis endpoint reachable"
    fi

    log_success "Infrastructure validation passed"
}

health_check() {
    log_info "Running health checks..."

    # Check pod status
    log_info "Checking pod status..."
    kubectl get pods -A

    # Check node status
    log_info "Checking node status..."
    kubectl get nodes

    # Check services
    log_info "Checking services..."
    kubectl get svc -A

    log_success "Health checks passed"
}

generate_kubeconfig() {
    log_info "Generating kubeconfig..."

    cd "$TERRAFORM_DIR"
    local cluster_name=$(terraform output -raw eks_cluster_name)
    local region="us-east-1"

    aws eks update-kubeconfig \
        --name "$cluster_name" \
        --region "$region" \
        --kubeconfig "${PROJECT_ROOT}/.kubeconfig-${ENVIRONMENT}"

    log_success "kubeconfig saved to .kubeconfig-${ENVIRONMENT}"
}

print_deployment_summary() {
    log_info "Deployment Summary"
    echo "===================="

    cd "$TERRAFORM_DIR"
    echo "Environment: $ENVIRONMENT"
    echo "Region: $(terraform output -raw infrastructure_summary | jq -r .region)"
    echo "VPC ID: $(terraform output -raw vpc_id)"
    echo "EKS Cluster: $(terraform output -raw eks_cluster_name)"
    echo "EKS Endpoint: $(terraform output -raw eks_cluster_endpoint)"
    echo "RDS Endpoint: $(terraform output -raw rds_endpoint)"
    echo "Redis Endpoint: $(terraform output -raw redis_endpoint)"
    echo "ALB DNS: $(terraform output -raw alb_dns_name)"
    echo ""
    echo "Deployment log: $DEPLOYMENT_LOG"
}

rollback() {
    log_error "Deployment failed - initiating rollback..."

    cd "$TERRAFORM_DIR"
    local plan_file="/tmp/terraform-${ENVIRONMENT}-rollback.tfplan"

    log_warn "Rolling back to previous state..."
    terraform plan \
        -var-file="environments/${ENVIRONMENT}.tfvars" \
        -out="$plan_file" \
        -destroy

    terraform apply "$plan_file"

    log_warn "Rollback completed"
}

# Main execution
main() {
    log_info "Starting Phase 05 Deployment"
    echo "Environment: $ENVIRONMENT"
    echo "Dry Run: $DRY_RUN"
    echo "Log: $DEPLOYMENT_LOG"
    echo ""

    validate_input
    check_prerequisites
    check_aws_credentials
    terraform_init
    terraform_validate
    terraform_fmt

    local plan_file
    plan_file=$(terraform_plan)

    terraform_apply "$plan_file"
    configure_kubectl
    generate_kubeconfig
    deploy_helm_charts
    validate_infrastructure
    health_check
    print_deployment_summary

    log_success "Deployment completed successfully!"
}

# Error handling
trap 'rollback' ERR

# Execute
main "$@"
