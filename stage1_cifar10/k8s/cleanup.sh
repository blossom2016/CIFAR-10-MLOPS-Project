#!/bin/bash

# MLOps FastAPI Kubernetes Cleanup Script
# This script removes all MLOps resources from Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning "This will delete ALL MLOps resources from the Kubernetes cluster!"
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleanup cancelled."
    exit 0
fi

print_status "Starting MLOps FastAPI cleanup..."

# Delete resources in reverse order of dependencies

# Delete HPA
print_status "Deleting HorizontalPodAutoscaler..."
kubectl delete -f hpa.yaml --ignore-not-found=true

# Delete Ingress
print_status "Deleting Ingress..."
kubectl delete -f ingress.yaml --ignore-not-found=true

# Delete Services
print_status "Deleting Services..."
kubectl delete -f service.yaml --ignore-not-found=true

# Delete Deployment
print_status "Deleting Deployment..."
kubectl delete -f deployment.yaml --ignore-not-found=true

# Delete Jobs
print_status "Deleting Jobs..."
kubectl delete -f job.yaml --ignore-not-found=true

# Delete PVC
print_status "Deleting PersistentVolumeClaim..."
kubectl delete -f pvc.yaml --ignore-not-found=true

# Delete ConfigMap and Secret
print_status "Deleting ConfigMap and Secret..."
kubectl delete -f configmap.yaml --ignore-not-found=true
kubectl delete -f secret.yaml --ignore-not-found=true

# Delete RBAC resources
print_status "Deleting RBAC resources..."
kubectl delete -f rbac.yaml --ignore-not-found=true

# Delete namespace (this will delete all remaining resources)
print_status "Deleting namespace..."
kubectl delete -f namespace.yaml --ignore-not-found=true

print_success "MLOps FastAPI cleanup completed successfully!"

# Alternative: Delete everything in the namespace at once
print_status "Alternative cleanup method - delete entire namespace:"
echo "  kubectl delete namespace mlops" 