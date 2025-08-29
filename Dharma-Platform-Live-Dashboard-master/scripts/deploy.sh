#!/bin/bash

# Project Dharma Deployment Script
# This script automates the deployment process with zero-downtime strategies

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-production}"
NAMESPACE="dharma-platform"
KUBECTL_TIMEOUT="300s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Project Dharma Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    deploy          Deploy all services
    deploy-service  Deploy specific service
    rollback        Rollback to previous version
    status          Check deployment status
    logs            View service logs
    scale           Scale services
    backup          Create backup before deployment

Options:
    -e, --environment   Environment (production, staging, development)
    -n, --namespace     Kubernetes namespace
    -s, --service       Service name (for service-specific commands)
    -r, --replicas      Number of replicas (for scaling)
    -v, --version       Image version/tag
    -h, --help          Show this help message

Examples:
    $0 deploy
    $0 deploy-service -s api-gateway-service -v v1.2.3
    $0 rollback -s ai-analysis-service
    $0 scale -s data-collection-service -r 5
    $0 status
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -s|--service)
                SERVICE="$2"
                shift 2
                ;;
            -r|--replicas)
                REPLICAS="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            deploy|deploy-service|rollback|status|logs|scale|backup)
                COMMAND="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("kubectl" "docker" "helm" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check kubectl connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE does not exist, creating..."
        kubectl create namespace "$NAMESPACE"
    fi
    
    log_success "Prerequisites check passed"
}

# Build and push Docker images
build_and_push_images() {
    local version="${VERSION:-$(git rev-parse --short HEAD)}"
    local registry="${DOCKER_REGISTRY:-dharma-platform}"
    
    log_info "Building and pushing Docker images (version: $version)..."
    
    local services=("api-gateway-service" "data-collection-service" "ai-analysis-service" 
                   "campaign-detection-service" "alert-management-service" "dashboard-service")
    
    for service in "${services[@]}"; do
        log_info "Building $service..."
        
        docker build \
            -t "$registry/$service:$version" \
            -t "$registry/$service:latest" \
            -f "services/$service/Dockerfile" \
            .
        
        log_info "Pushing $service..."
        docker push "$registry/$service:$version"
        docker push "$registry/$service:latest"
    done
    
    log_success "All images built and pushed successfully"
}

# Apply Kubernetes manifests
apply_manifests() {
    log_info "Applying Kubernetes manifests..."
    
    local manifests_dir="$PROJECT_ROOT/infrastructure/kubernetes"
    
    # Apply in order
    local manifest_files=(
        "namespace.yaml"
        "configmap.yaml"
        "secrets.yaml"
        "persistent-volumes.yaml"
        "databases.yaml"
        "services.yaml"
        "ingress.yaml"
    )
    
    for manifest in "${manifest_files[@]}"; do
        if [[ -f "$manifests_dir/$manifest" ]]; then
            log_info "Applying $manifest..."
            kubectl apply -f "$manifests_dir/$manifest"
        else
            log_warning "Manifest $manifest not found, skipping..."
        fi
    done
    
    log_success "Kubernetes manifests applied successfully"
}

# Wait for deployment to be ready
wait_for_deployment() {
    local service="$1"
    local timeout="${2:-$KUBECTL_TIMEOUT}"
    
    log_info "Waiting for $service deployment to be ready..."
    
    if kubectl rollout status deployment/"$service" -n "$NAMESPACE" --timeout="$timeout"; then
        log_success "$service deployment is ready"
        return 0
    else
        log_error "$service deployment failed or timed out"
        return 1
    fi
}

# Deploy all services
deploy_all() {
    log_info "Starting full deployment to $ENVIRONMENT environment..."
    
    # Create backup before deployment
    create_backup
    
    # Build and push images
    build_and_push_images
    
    # Apply manifests
    apply_manifests
    
    # Wait for all deployments
    local services=("api-gateway-service" "data-collection-service" "ai-analysis-service" 
                   "campaign-detection-service" "alert-management-service" "dashboard-service")
    
    for service in "${services[@]}"; do
        wait_for_deployment "$service"
    done
    
    # Run health checks
    run_health_checks
    
    log_success "Full deployment completed successfully"
}

# Deploy specific service
deploy_service() {
    local service="${SERVICE:-}"
    local version="${VERSION:-$(git rev-parse --short HEAD)}"
    
    if [[ -z "$service" ]]; then
        log_error "Service name is required for service deployment"
        exit 1
    fi
    
    log_info "Deploying service: $service (version: $version)"
    
    # Build and push image for specific service
    local registry="${DOCKER_REGISTRY:-dharma-platform}"
    
    log_info "Building $service..."
    docker build \
        -t "$registry/$service:$version" \
        -t "$registry/$service:latest" \
        -f "services/$service/Dockerfile" \
        .
    
    log_info "Pushing $service..."
    docker push "$registry/$service:$version"
    
    # Update deployment with new image
    kubectl set image deployment/"$service" \
        "$service"="$registry/$service:$version" \
        -n "$NAMESPACE"
    
    # Wait for rollout
    wait_for_deployment "$service"
    
    # Run health check for specific service
    run_service_health_check "$service"
    
    log_success "Service $service deployed successfully"
}

# Rollback deployment
rollback_deployment() {
    local service="${SERVICE:-}"
    
    if [[ -z "$service" ]]; then
        log_error "Service name is required for rollback"
        exit 1
    fi
    
    log_info "Rolling back service: $service"
    
    # Get rollout history
    kubectl rollout history deployment/"$service" -n "$NAMESPACE"
    
    # Rollback to previous version
    kubectl rollout undo deployment/"$service" -n "$NAMESPACE"
    
    # Wait for rollback to complete
    wait_for_deployment "$service"
    
    log_success "Service $service rolled back successfully"
}

# Scale deployment
scale_deployment() {
    local service="${SERVICE:-}"
    local replicas="${REPLICAS:-}"
    
    if [[ -z "$service" || -z "$replicas" ]]; then
        log_error "Service name and replica count are required for scaling"
        exit 1
    fi
    
    log_info "Scaling service $service to $replicas replicas"
    
    kubectl scale deployment/"$service" --replicas="$replicas" -n "$NAMESPACE"
    
    wait_for_deployment "$service"
    
    log_success "Service $service scaled to $replicas replicas"
}

# Check deployment status
check_status() {
    log_info "Checking deployment status in namespace: $NAMESPACE"
    
    echo
    log_info "Deployments:"
    kubectl get deployments -n "$NAMESPACE" -o wide
    
    echo
    log_info "Pods:"
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo
    log_info "Services:"
    kubectl get services -n "$NAMESPACE" -o wide
    
    echo
    log_info "Ingress:"
    kubectl get ingress -n "$NAMESPACE" -o wide
}

# View logs
view_logs() {
    local service="${SERVICE:-}"
    
    if [[ -z "$service" ]]; then
        log_error "Service name is required for viewing logs"
        exit 1
    fi
    
    log_info "Viewing logs for service: $service"
    kubectl logs -f deployment/"$service" -n "$NAMESPACE"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    local services=("api-gateway-service" "data-collection-service" "ai-analysis-service" 
                   "campaign-detection-service" "alert-management-service" "dashboard-service")
    
    for service in "${services[@]}"; do
        run_service_health_check "$service"
    done
    
    log_success "All health checks passed"
}

# Run health check for specific service
run_service_health_check() {
    local service="$1"
    local max_attempts=30
    local attempt=1
    
    log_info "Running health check for $service..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if kubectl exec -n "$NAMESPACE" \
            "$(kubectl get pods -n "$NAMESPACE" -l app="$service" -o jsonpath='{.items[0].metadata.name}')" \
            -- curl -f http://localhost:8000/health &> /dev/null; then
            log_success "$service health check passed"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 10
        ((attempt++))
    done
    
    log_error "$service health check failed after $max_attempts attempts"
    return 1
}

# Create backup
create_backup() {
    log_info "Creating backup before deployment..."
    
    local backup_dir="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup database
    log_info "Backing up PostgreSQL database..."
    kubectl exec -n "$NAMESPACE" \
        "$(kubectl get pods -n "$NAMESPACE" -l app=postgresql -o jsonpath='{.items[0].metadata.name}')" \
        -- pg_dump -U dharma dharma_platform > "$backup_dir/postgresql_backup.sql"
    
    # Backup MongoDB
    log_info "Backing up MongoDB database..."
    kubectl exec -n "$NAMESPACE" \
        "$(kubectl get pods -n "$NAMESPACE" -l app=mongodb -o jsonpath='{.items[0].metadata.name}')" \
        -- mongodump --db dharma_platform --archive > "$backup_dir/mongodb_backup.archive"
    
    # Backup Kubernetes manifests
    log_info "Backing up Kubernetes manifests..."
    kubectl get all -n "$NAMESPACE" -o yaml > "$backup_dir/kubernetes_manifests.yaml"
    
    log_success "Backup created at: $backup_dir"
}

# Main function
main() {
    local command="${COMMAND:-}"
    
    if [[ -z "$command" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
    
    check_prerequisites
    
    case "$command" in
        deploy)
            deploy_all
            ;;
        deploy-service)
            deploy_service
            ;;
        rollback)
            rollback_deployment
            ;;
        scale)
            scale_deployment
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        backup)
            create_backup
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Parse arguments and run main function
parse_args "$@"
main