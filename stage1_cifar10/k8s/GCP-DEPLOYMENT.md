# GCP GKE Deployment Guide

This guide shows how to deploy your MLOps FastAPI application to Google Cloud Platform (GCP) using Kubernetes manifests instead of Helm.

## 🏗️ Your GCP Setup

Based on your existing configuration:

- **Project ID**: `my-mlops-project2`
- **GKE Cluster**: `mlops-cluster` in `us-central1-a`
- **Docker Images**: `gcr.io/my-mlops-project2/vision-inference:v0.1.0`
- **GCS Bucket**: `my-mlops-project2-mlops-artifacts`

## 📦 Where Are Your Docker Images?

Your Docker images are stored in **Google Container Registry (GCR)**:

```bash
# Your image location
gcr.io/my-mlops-project2/vision-inference:v0.1.0

# To see all your images
gcloud container images list --repository=gcr.io/my-mlops-project2

# To see tags for a specific image
gcloud container images list-tags gcr.io/my-mlops-project2/vision-inference --limit=10
```

## 🚀 Quick Deployment (Recommended)

### Option 1: Simple Deployment

```bash
cd stage1_cifar10/k8s
./deploy-gcp-simple.sh
```

This script:
- ✅ Uses your existing GKE cluster
- ✅ Uses your existing GCR images
- ✅ Downloads model from your GCS bucket
- ✅ Creates LoadBalancer service for external access

### Option 2: Full Deployment with Cluster Creation

```bash
cd stage1_cifar10/k8s
./deploy-gcp.sh
```

This script:
- ✅ Creates GKE cluster if needed
- ✅ Creates GCS bucket if needed
- ✅ Uploads model to GCS
- ✅ Builds and pushes Docker image
- ✅ Deploys everything

## 📋 Manual Deployment Steps

If you prefer to deploy manually:

### 1. Connect to Your GKE Cluster

```bash
# Set project
gcloud config set project my-mlops-project2

# Get cluster credentials
gcloud container clusters get-credentials mlops-cluster --zone us-central1-a
```

### 2. Deploy Kubernetes Resources

```bash
cd stage1_cifar10/k8s

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
kubectl wait --for=condition=Bound pvc/mlops-artifacts-pvc -n mlops --timeout=60s

# Apply GCP-specific deployment (with init container)
kubectl apply -f deployment-gcp.yaml

# Apply GCP-specific services
kubectl apply -f service-gcp.yaml

# Apply HPA
kubectl apply -f hpa.yaml

# Wait for deployment
kubectl wait --for=condition=available --timeout=300s deployment/mlops-fastapi -n mlops
```

### 3. Check Deployment Status

```bash
# Check pods
kubectl get pods -n mlops

# Check services
kubectl get svc -n mlops

# Check logs
kubectl logs -f deployment/mlops-fastapi -n mlops
```

## 🌐 Accessing Your Application

### External Access (LoadBalancer)

The deployment creates a LoadBalancer service that provides external access:

```bash
# Get external IP
kubectl get svc mlops-fastapi-service -n mlops

# Test the API
curl http://<EXTERNAL_IP>/health
curl http://<EXTERNAL_IP>/
```

### Internal Access

```bash
# Port forward for local access
kubectl port-forward svc/mlops-fastapi-internal 8080:80 -n mlops

# Then access at http://localhost:8080
```

### NodePort Access

```bash
# Get NodePort service details
kubectl get svc mlops-fastapi-nodeport -n mlops

# Access via node IP and port 30080
```

## 🔧 Key Features of GCP Deployment

### 1. Init Container for Model Download

The `deployment-gcp.yaml` includes an init container that downloads your model from GCS:

```yaml
initContainers:
  - name: model-downloader
    image: google/cloud-sdk:slim
    command:
      - /bin/sh
      - -c
      - |
        gsutil cp gs://my-mlops-project2-mlops-artifacts/model.pt /models/model.pt
```

### 2. GCR Image Integration

Uses your existing GCR images:
```yaml
image: gcr.io/my-mlops-project2/vision-inference:v0.1.0
```

### 3. LoadBalancer Service

Provides external access with automatic IP assignment:
```yaml
type: LoadBalancer
```

### 4. GCP-Specific Annotations

```yaml
annotations:
  cloud.google.com/load-balancer-type: "External"
```

## 📊 Monitoring and Management

### Check Application Status

```bash
# Health check
curl http://<EXTERNAL_IP>/health

# Ready check
curl http://<EXTERNAL_IP>/ready

# Metrics
curl http://<EXTERNAL_IP>/metrics
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment mlops-fastapi --replicas=5 -n mlops

# Check HPA
kubectl get hpa -n mlops
```

### Logs and Debugging

```bash
# Application logs
kubectl logs -f deployment/mlops-fastapi -n mlops

# Init container logs
kubectl logs -f deployment/mlops-fastapi -c model-downloader -n mlops

# Pod details
kubectl describe pod <pod-name> -n mlops
```

## 🧹 Cleanup

### Remove All Resources

```bash
# Delete entire namespace (removes everything)
kubectl delete namespace mlops

# Or use the cleanup script
./cleanup.sh
```

### Remove GKE Cluster (if created by script)

```bash
gcloud container clusters delete mlops-cluster --zone us-central1-a
```

## 🔍 Troubleshooting

### Common Issues

1. **Image Pull Errors**
   ```bash
   kubectl describe pod <pod-name> -n mlops
   # Check if image exists: gcloud container images list-tags gcr.io/my-mlops-project2/vision-inference
   ```

2. **Model Download Failures**
   ```bash
   kubectl logs -f deployment/mlops-fastapi -c model-downloader -n mlops
   # Check if model exists: gsutil ls gs://my-mlops-project2-mlops-artifacts/
   ```

3. **LoadBalancer Not Ready**
   ```bash
   kubectl get svc mlops-fastapi-service -n mlops -w
   # Wait for external IP to be assigned
   ```

4. **PVC Not Bound**
   ```bash
   kubectl get pvc -n mlops
   kubectl describe pvc mlops-artifacts-pvc -n mlops
   ```

### Debug Commands

```bash
# Check all resources
kubectl get all -n mlops

# Check events
kubectl get events -n mlops --sort-by='.lastTimestamp'

# Check node resources
kubectl top nodes
kubectl top pods -n mlops
```

## 💰 Cost Optimization

### GKE Cluster Optimization

```bash
# Scale down cluster when not in use
gcloud container clusters resize mlops-cluster --num-nodes=1 --zone us-central1-a

# Scale up when needed
gcloud container clusters resize mlops-cluster --num-nodes=2 --zone us-central1-a
```

### Application Optimization

```bash
# Scale down application
kubectl scale deployment mlops-fastapi --replicas=1 -n mlops

# Adjust HPA settings
kubectl patch hpa mlops-fastapi-hpa -n mlops -p '{"spec":{"minReplicas":1}}'
```

## 🔐 Security Best Practices

1. **Update Secrets**: Replace placeholder values in `secret.yaml`
2. **Network Policies**: Consider implementing network policies
3. **RBAC**: Review and adjust RBAC permissions
4. **Image Scanning**: Enable container image vulnerability scanning
5. **Audit Logging**: Enable GKE audit logs

## 📈 Next Steps

1. **Set up monitoring**: Configure Prometheus and Grafana
2. **Implement CI/CD**: Set up automated deployments
3. **Add SSL/TLS**: Configure HTTPS with cert-manager
4. **Set up logging**: Configure centralized logging with Stackdriver
5. **Implement backup**: Set up regular backups of persistent data 