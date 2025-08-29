# MLOps FastAPI Kubernetes Deployment

This directory contains all the Kubernetes manifests and deployment scripts for the MLOps FastAPI application.

## 📁 File Structure

```
k8s/
├── namespace.yaml          # Namespace for organizing resources
├── configmap.yaml          # Application configuration
├── secret.yaml            # Sensitive data (API keys, etc.)
├── pvc.yaml              # Persistent volume for model storage
├── deployment.yaml        # Main FastAPI application deployment
├── service.yaml          # Network services (ClusterIP, NodePort, LoadBalancer)
├── ingress.yaml          # External access configuration
├── hpa.yaml              # Horizontal Pod Autoscaler
├── job.yaml              # Training and evaluation jobs
├── rbac.yaml             # Role-based access control
├── deploy.sh             # Deployment script
├── cleanup.sh            # Cleanup script
└── README.md             # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster**: A running Kubernetes cluster (local or cloud)
2. **kubectl**: Kubernetes command-line tool
3. **Docker Image**: The FastAPI application image built and available

### 1. Build and Push Docker Image

```bash
# Build the image
docker build -t mlops-fastapi:latest .

# Tag for your registry (replace with your registry)
docker tag mlops-fastapi:latest your-registry/mlops-fastapi:latest

# Push to registry
docker push your-registry/mlops-fastapi:latest
```

### 2. Update Image Reference

Edit `deployment.yaml` and `job.yaml` to use your actual image:

```yaml
image: your-registry/mlops-fastapi:latest
```

### 3. Deploy the Application

```bash
# Make scripts executable
chmod +x deploy.sh cleanup.sh

# Deploy everything
./deploy.sh
```

### 4. Access the Application

```bash
# Port forward to access the service
kubectl port-forward svc/mlops-fastapi-service 8080:80 -n mlops

# Or use NodePort service
kubectl get svc mlops-fastapi-nodeport -n mlops
```

## 📋 Detailed Configuration

### Namespace (`namespace.yaml`)

Creates a dedicated namespace `mlops` for all resources.

### ConfigMap (`configmap.yaml`)

Contains application configuration:
- Model paths
- API settings
- Class labels
- Logging configuration

### Secret (`secret.yaml`)

Stores sensitive data (base64 encoded):
- API keys
- Database URLs
- Redis URLs

**⚠️ Important**: Update the secret values with your actual data:

```bash
echo -n "your-actual-api-key" | base64
```

### PersistentVolumeClaim (`pvc.yaml`)

Provides persistent storage for:
- Model artifacts
- Training data
- Logs

### Deployment (`deployment.yaml`)

Main application deployment with:
- 3 replicas for high availability
- Health checks (liveness and readiness probes)
- Resource limits and requests
- Security context
- Environment variables from ConfigMap and Secret

### Services (`service.yaml`)

Multiple service types:
- **ClusterIP**: Internal cluster access
- **NodePort**: Development/testing access
- **LoadBalancer**: External access (commented out)

### Ingress (`ingress.yaml`)

External access configuration:
- SSL/TLS support
- Domain routing
- Load balancing

**⚠️ Important**: Update the host domain in `ingress.yaml`.

### HorizontalPodAutoscaler (`hpa.yaml`)

Automatic scaling based on:
- CPU utilization (70%)
- Memory utilization (80%)
- Min: 2 replicas, Max: 10 replicas

### Jobs (`job.yaml`)

Batch processing for:
- Model training
- Model evaluation

### RBAC (`rbac.yaml`)

Security and permissions:
- Service account
- Role and role binding
- Minimal required permissions

## 🔧 Customization

### Environment Variables

Update `configmap.yaml` to modify:
- Model paths
- API settings
- Logging levels

### Resource Limits

Modify resource requests/limits in `deployment.yaml`:

```yaml
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 2Gi
```

### Scaling Configuration

Adjust HPA settings in `hpa.yaml`:

```yaml
minReplicas: 2
maxReplicas: 10
```

### Storage

Modify PVC size in `pvc.yaml`:

```yaml
resources:
  requests:
    storage: 5Gi
```

## 📊 Monitoring

### Health Checks

The application provides health check endpoints:
- `/health` - Liveness probe
- `/ready` - Readiness probe
- `/metrics` - Prometheus metrics

### Logs

```bash
# View application logs
kubectl logs -f deployment/mlops-fastapi -n mlops

# View logs from specific pod
kubectl logs -f <pod-name> -n mlops
```

### Metrics

```bash
# Check HPA status
kubectl get hpa -n mlops

# Check pod metrics
kubectl top pods -n mlops
```

## 🧹 Cleanup

### Remove All Resources

```bash
./cleanup.sh
```

### Manual Cleanup

```bash
# Delete specific resources
kubectl delete -f deployment.yaml
kubectl delete -f service.yaml

# Delete entire namespace
kubectl delete namespace mlops
```

## 🔍 Troubleshooting

### Common Issues

1. **Image Pull Errors**
   ```bash
   kubectl describe pod <pod-name> -n mlops
   ```

2. **PVC Not Bound**
   ```bash
   kubectl get pvc -n mlops
   kubectl describe pvc mlops-artifacts-pvc -n mlops
   ```

3. **Service Not Accessible**
   ```bash
   kubectl get svc -n mlops
   kubectl describe svc mlops-fastapi-service -n mlops
   ```

4. **HPA Not Working**
   ```bash
   kubectl get hpa -n mlops
   kubectl describe hpa mlops-fastapi-hpa -n mlops
   ```

### Debug Commands

```bash
# Check all resources
kubectl get all -n mlops

# Check events
kubectl get events -n mlops --sort-by='.lastTimestamp'

# Check pod status
kubectl get pods -n mlops -o wide

# Exec into pod
kubectl exec -it <pod-name> -n mlops -- /bin/bash
```

## 🔐 Security Considerations

1. **Secrets**: Never commit actual secret values to version control
2. **RBAC**: Use minimal required permissions
3. **Network Policies**: Consider implementing network policies
4. **Pod Security**: Run containers as non-root users
5. **Image Scanning**: Regularly scan container images for vulnerabilities

## 📈 Production Considerations

1. **High Availability**: Use multiple replicas and anti-affinity
2. **Monitoring**: Implement comprehensive monitoring and alerting
3. **Backup**: Regular backups of persistent data
4. **Updates**: Implement rolling update strategies
5. **Security**: Use image signing and admission controllers

## 🤝 Contributing

When modifying these manifests:
1. Test changes in a development environment
2. Update documentation
3. Follow Kubernetes best practices
4. Consider backward compatibility 