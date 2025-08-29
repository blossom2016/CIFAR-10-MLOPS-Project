#!/bin/bash

# MLOps FastAPI Kubernetes Deployment Script
# This script deploys the complete MLOps application to Kubernetes

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

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if we can connect to a cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

print_status "Starting MLOps FastAPI deployment..."

# Create namespace first
print_status "Creating namespace..."
kubectl apply -f namespace.yaml

# Apply RBAC resources
print_status "Applying RBAC resources..."
kubectl apply -f rbac.yaml

# Apply ConfigMap and Secret
print_status "Applying ConfigMap and Secret..."
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# Apply PVC
print_status "Applying PersistentVolumeClaim..."
kubectl apply -f pvc.yaml

# Wait for PVC to be bound
print_status "Waiting for PVC to be bound..."
kubectl wait --for=condition=Bound pvc/mlops-artifacts-pvc -n mlops --timeout=60s

# Apply Deployment
print_status "Applying Deployment..."
kubectl apply -f deployment.yaml

# Apply Services
print_status "Applying Services..."
kubectl apply -f service.yaml

# Apply Ingress (optional - uncomment if you have ingress controller)
# print_status "Applying Ingress..."
# kubectl apply -f ingress.yaml

# Apply HPA
print_status "Applying HorizontalPodAutoscaler..."
kubectl apply -f hpa.yaml

# Wait for deployment to be ready
print_status "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/mlops-fastapi -n mlops

# Get service information
print_status "Getting service information..."
kubectl get svc -n mlops

# Get pod status
print_status "Getting pod status..."
kubectl get pods -n mlops

print_success "MLOps FastAPI deployment completed successfully!"

# Optional: Show how to access the service
print_status "To access the service:"
echo "  - ClusterIP: kubectl port-forward svc/mlops-fastapi-service 8080:80 -n mlops"
echo "  - NodePort: kubectl get svc mlops-fastapi-nodeport -n mlops"
echo "  - LoadBalancer: kubectl get svc mlops-fastapi-lb -n mlops (if enabled)"

print_status "To check logs:"
echo "  kubectl logs -f deployment/mlops-fastapi -n mlops"

print_status "To scale the deployment:"
echo "  kubectl scale deployment mlops-fastapi --replicas=5 -n mlops" 