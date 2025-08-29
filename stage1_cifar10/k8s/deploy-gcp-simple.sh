#!/bin/bash

# Simple GCP GKE Deployment Script
# Uses GCP-specific Kubernetes manifests

set -e

# GCP Configuration
PROJECT_ID="${PROJECT_ID:-my-mlops-project2}"
GCP_ZONE="${GCP_ZONE:-us-central1-a}"
CLUSTER_NAME="${CLUSTER_NAME:-mlops-cluster}"

echo "🚀 Deploying MLOps FastAPI to GCP GKE"
echo "Project: ${PROJECT_ID}"
echo "Cluster: ${CLUSTER_NAME}"
echo "Zone: ${GCP_ZONE}"
echo

# Check if cluster exists and get credentials
if gcloud container clusters describe "${CLUSTER_NAME}" --zone "${GCP_ZONE}" >/dev/null 2>&1; then
    echo "✅ Cluster ${CLUSTER_NAME} exists, getting credentials..."
    gcloud container clusters get-credentials "${CLUSTER_NAME}" --zone "${GCP_ZONE}"
else
    echo "❌ Cluster ${CLUSTER_NAME} not found!"
    echo "Please create the cluster first or update CLUSTER_NAME variable."
    exit 1
fi

# Set project
gcloud config set project "${PROJECT_ID}"

# Deploy using GCP-specific manifests
echo "📦 Deploying Kubernetes resources..."

# Create namespace
kubectl apply -f namespace.yaml

# Apply RBAC
kubectl apply -f rbac.yaml

# Apply ConfigMap and Secret
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# Apply PVC
kubectl apply -f pvc.yaml

# Wait for PVC
echo "⏳ Waiting for PVC to be bound..."
kubectl wait --for=condition=Bound pvc/mlops-artifacts-pvc -n mlops --timeout=60s

# Apply GCP-specific deployment (with init container for GCS)
kubectl apply -f deployment-gcp.yaml

# Apply GCP-specific services
kubectl apply -f service-gcp.yaml

# Apply HPA
kubectl apply -f hpa.yaml

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/mlops-fastapi -n mlops

echo "✅ Deployment completed!"

# Show status
echo "📊 Pod status:"
kubectl get pods -n mlops

echo "🌐 Services:"
kubectl get svc -n mlops

# Get external IP
EXTERNAL_IP=$(kubectl get svc mlops-fastapi-service -n mlops -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
if [ -n "${EXTERNAL_IP}" ]; then
    echo "🎉 External IP: ${EXTERNAL_IP}"
    echo "   API: http://${EXTERNAL_IP}"
    echo "   Health: http://${EXTERNAL_IP}/health"
    echo "   Test: curl -X POST http://${EXTERNAL_IP}/predict -F 'file=@your-image.jpg'"
else
    echo "📝 No external IP yet. LoadBalancer is still provisioning..."
    echo "   Check with: kubectl get svc mlops-fastapi-service -n mlops -w"
fi

echo
echo "🔧 Useful commands:"
echo "   Logs: kubectl logs -f deployment/mlops-fastapi -n mlops"
echo "   Scale: kubectl scale deployment mlops-fastapi --replicas=5 -n mlops"
echo "   HPA: kubectl get hpa -n mlops"
echo "   Delete: kubectl delete namespace mlops" 