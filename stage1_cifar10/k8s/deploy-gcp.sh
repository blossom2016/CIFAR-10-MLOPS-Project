#!/bin/bash

# MLOps FastAPI GCP GKE Deployment Script
# This script deploys the MLOps application to GCP GKE using Kubernetes manifests

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

# GCP Configuration
PROJECT_ID="${PROJECT_ID:-my-mlops-project2}"
GCP_ZONE="${GCP_ZONE:-us-central1-a}"
CLUSTER_NAME="${CLUSTER_NAME:-mlops-cluster}"
GCR_REGION="${GCR_REGION:-gcr.io}"
IMAGE_REPO="${IMAGE_REPO:-${GCR_REGION}/${PROJECT_ID}/vision-inference}"
IMAGE_TAG="${IMAGE_TAG:-v0.1.0}"
GCS_BUCKET="${GCS_BUCKET:-${PROJECT_ID}-mlops-artifacts}"

print_status "GCP Configuration:"
echo "  Project ID: ${PROJECT_ID}"
echo "  Zone: ${GCP_ZONE}"
echo "  Cluster: ${CLUSTER_NAME}"
echo "  Image: ${IMAGE_REPO}:${IMAGE_TAG}"
echo "  GCS Bucket: ${GCS_BUCKET}"
echo

# Check prerequisites
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install Google Cloud SDK."
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl."
    exit 1
fi

# Set GCP project
print_status "Setting GCP project..."
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
print_status "Enabling required APIs..."
gcloud services enable container.googleapis.com containerregistry.googleapis.com storage.googleapis.com --project "${PROJECT_ID}"

# Check if cluster exists
if ! gcloud container clusters describe "${CLUSTER_NAME}" --zone "${GCP_ZONE}" >/dev/null 2>&1; then
    print_status "Creating GKE cluster ${CLUSTER_NAME}..."
    gcloud container clusters create "${CLUSTER_NAME}" \
        --zone "${GCP_ZONE}" \
        --num-nodes=2 \
        --machine-type=e2-standard-2 \
        --enable-ip-alias
else
    print_status "Cluster ${CLUSTER_NAME} already exists."
fi

# Get cluster credentials
print_status "Getting cluster credentials..."
gcloud container clusters get-credentials "${CLUSTER_NAME}" --zone "${GCP_ZONE}"

# Configure Docker for GCR
print_status "Configuring Docker for GCR..."
gcloud auth configure-docker --quiet

# Create GCS bucket if it doesn't exist
if ! gsutil ls -b "gs://${GCS_BUCKET}" >/dev/null 2>&1; then
    print_status "Creating GCS bucket gs://${GCS_BUCKET}..."
    gsutil mb -l "${GCP_ZONE%?-?}" "gs://${GCS_BUCKET}"
else
    print_status "GCS bucket gs://${GCS_BUCKET} already exists."
fi

# Upload model to GCS if it exists locally
MODEL_LOCAL_PATH="./artifacts/model.pt"
if [ -f "${MODEL_LOCAL_PATH}" ]; then
    print_status "Uploading model to GCS..."
    gsutil cp "${MODEL_LOCAL_PATH}" "gs://${GCS_BUCKET}/model.pt"
    print_success "Model uploaded to gs://${GCS_BUCKET}/model.pt"
else
    print_warning "Model file not found at ${MODEL_LOCAL_PATH}. You'll need to upload it manually."
fi

# Update Kubernetes manifests with GCP-specific values
print_status "Updating Kubernetes manifests for GCP..."

# Update deployment.yaml with GCR image
sed -i.bak "s|image: mlops-fastapi:latest|image: ${IMAGE_REPO}:${IMAGE_TAG}|g" deployment.yaml

# Update job.yaml with GCR image
sed -i.bak "s|image: mlops-fastapi:latest|image: ${IMAGE_REPO}:${IMAGE_TAG}|g" job.yaml

# Update configmap.yaml with GCS bucket
sed -i.bak "s|MODEL_PATH: \"/app/artifacts/model.pt\"|MODEL_PATH: \"/app/artifacts/model.pt\"|g" configmap.yaml

# Update secret.yaml with GCP-specific values (you should update these with real values)
print_warning "Please update secret.yaml with your actual GCP credentials and API keys."

# Deploy to Kubernetes
print_status "Deploying to Kubernetes..."

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

print_success "MLOps FastAPI deployment to GCP GKE completed successfully!"

# Show access information
print_status "Access Information:"
echo "  - ClusterIP: kubectl port-forward svc/mlops-fastapi-service 8080:80 -n mlops"
echo "  - NodePort: kubectl get svc mlops-fastapi-nodeport -n mlops"
echo "  - LoadBalancer: kubectl get svc mlops-fastapi-lb -n mlops (if enabled)"

# Check if LoadBalancer service has external IP
EXTERNAL_IP=$(kubectl get svc mlops-fastapi-service -n mlops -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
if [ -n "${EXTERNAL_IP}" ]; then
    print_success "External IP: ${EXTERNAL_IP}"
    echo "  API endpoint: http://${EXTERNAL_IP}"
    echo "  Health check: http://${EXTERNAL_IP}/health"
    echo "  Prediction: curl -X POST http://${EXTERNAL_IP}/predict -F 'file=@your-image.jpg'"
fi

print_status "Useful commands:"
echo "  - View logs: kubectl logs -f deployment/mlops-fastapi -n mlops"
echo "  - Scale deployment: kubectl scale deployment mlops-fastapi --replicas=5 -n mlops"
echo "  - Check HPA: kubectl get hpa -n mlops"
echo "  - Access cluster: gcloud container clusters get-credentials ${CLUSTER_NAME} --zone ${GCP_ZONE}"

# Clean up backup files
rm -f *.bak 