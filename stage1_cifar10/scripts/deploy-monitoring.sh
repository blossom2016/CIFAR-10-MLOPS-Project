#!/bin/bash

# Deploy Monitoring Infrastructure for CIFAR-10 ML Project
# This script sets up Prometheus, Grafana, and monitoring configurations

set -e

echo "🚀 Deploying monitoring infrastructure..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Not connected to a Kubernetes cluster"
    exit 1
fi

print_status "Connected to cluster: $(kubectl config current-context)"

# Create monitoring namespace
print_status "Creating monitoring namespace..."
kubectl apply -f k8s/monitoring.yaml

# Wait for namespace to be created
kubectl wait --for=condition=Active namespace/monitoring --timeout=30s

# Deploy Prometheus
print_status "Deploying Prometheus..."
kubectl apply -f k8s/monitoring.yaml -n monitoring

# Wait for Prometheus to be ready
print_status "Waiting for Prometheus to be ready..."
kubectl wait --for=condition=available deployment/prometheus -n monitoring --timeout=120s

# Deploy Grafana
print_status "Deploying Grafana..."
kubectl apply -f k8s/monitoring.yaml -n monitoring

# Wait for Grafana to be ready
print_status "Waiting for Grafana to be ready..."
kubectl wait --for=condition=available deployment/grafana -n monitoring --timeout=120s

# Get service URLs
print_status "Getting service URLs..."

PROMETHEUS_URL=$(kubectl get service prometheus-service -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$PROMETHEUS_URL" ]; then
    PROMETHEUS_URL=$(kubectl get service prometheus-service -n monitoring -o jsonpath='{.spec.clusterIP}')
fi
PROMETHEUS_PORT=$(kubectl get service prometheus-service -n monitoring -o jsonpath='{.spec.ports[0].nodePort}')

GRAFANA_URL=$(kubectl get service grafana-service -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$GRAFANA_URL" ]; then
    GRAFANA_URL=$(kubectl get service grafana-service -n monitoring -o jsonpath='{.spec.clusterIP}')
fi
GRAFANA_PORT=$(kubectl get service grafana-service -n monitoring -o jsonpath='{.spec.ports[0].nodePort}')

print_status "Monitoring services deployed successfully!"
echo ""
echo "📊 Monitoring URLs:"
echo "  Prometheus: http://$PROMETHEUS_URL:$PROMETHEUS_PORT"
echo "  Grafana:    http://$GRAFANA_URL:$GRAFANA_PORT"
echo ""
echo "🔐 Grafana credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""

# Import Grafana dashboard
print_status "Importing Grafana dashboard..."
# Note: You'll need to manually import the dashboard from monitoring/grafana-dashboard.json
print_warning "Please manually import the dashboard from monitoring/grafana-dashboard.json in Grafana"

# Check if CIFAR-10 API is running
print_status "Checking CIFAR-10 API status..."
if kubectl get deployment cifar10-deployment -n default &> /dev/null; then
    print_status "CIFAR-10 API is running. Updating with monitoring annotations..."
    kubectl apply -f k8s/monitoring.yaml
else
    print_warning "CIFAR-10 API not found. Deploy it first to enable monitoring."
fi

# Create monitoring alerts (optional)
print_status "Setting up basic monitoring alerts..."

cat << EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1alpha1
kind: PrometheusRule
metadata:
  name: cifar10-alerts
  namespace: monitoring
spec:
  groups:
  - name: cifar10.rules
    rules:
    - alert: HighErrorRate
      expr: rate(cifar10_errors_total[5m]) > 0.1
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ \$value }} errors per second"
    
    - alert: ModelNotLoaded
      expr: cifar10_model_loaded == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Model is not loaded"
        description: "The ML model is not loaded in the application"
    
    - alert: HighMemoryUsage
      expr: cifar10_system_memory_bytes / 1024 / 1024 / 1024 > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage"
        description: "Memory usage is {{ \$value }} GB"
    
    - alert: HighCPUUsage
      expr: cifar10_system_cpu_percent > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage"
        description: "CPU usage is {{ \$value }}%"
EOF

print_status "✅ Monitoring infrastructure deployed successfully!"
echo ""
echo "📋 Next steps:"
echo "  1. Access Grafana at http://$GRAFANA_URL:$GRAFANA_PORT"
echo "  2. Login with admin/admin123"
echo "  3. Import the dashboard from monitoring/grafana-dashboard.json"
echo "  4. Test the CIFAR-10 API to see metrics in Prometheus"
echo "  5. Set up alerts and notifications as needed"
echo ""
echo "🔍 Useful commands:"
echo "  kubectl get pods -n monitoring"
echo "  kubectl logs -f deployment/prometheus -n monitoring"
echo "  kubectl logs -f deployment/grafana -n monitoring"
echo "  kubectl port-forward service/prometheus-service 9090:9090 -n monitoring"
echo "  kubectl port-forward service/grafana-service 3000:3000 -n monitoring"
