#!/usr/bin/env bash
set -euo pipefail

# --- USER CONFIG ---
# Edit these before running, or export them in your shell
PROJECT_ID="${PROJECT_ID:-my-mlops-project2}"   # <- change or export
GCP_ZONE="${GCP_ZONE:-us-central1-a}"
CLUSTER_NAME="${CLUSTER_NAME:-mlops-cluster}"
CLUSTER_MACHINE_TYPE="${CLUSTER_MACHINE_TYPE:-e2-standard-2}"
CLUSTER_NODE_COUNT="${CLUSTER_NODE_COUNT:-2}"
GCR_REGION="${GCR_REGION:-gcr.io}"  # using gcr.io (global)
IMAGE_REPO="${IMAGE_REPO:-${GCR_REGION}/${PROJECT_ID}/vision-inference}"
IMAGE_TAG="${IMAGE_TAG:-v0.1.0}"
GCS_BUCKET="${GCS_BUCKET:-${PROJECT_ID}-mlops-artifacts}"
MODEL_LOCAL_PATH="${MODEL_LOCAL_PATH:-./artifacts/model.pt}"
# --------------------

echo "Using Project: ${PROJECT_ID}"
echo "Cluster: ${CLUSTER_NAME} in ${GCP_ZONE}"
echo "Image will be pushed as: ${IMAGE_REPO}:${IMAGE_TAG}"
echo "GCS bucket: ${GCS_BUCKET}"
echo

# 1) Set project
gcloud config set project "${PROJECT_ID}"

# 2) Enable necessary APIs
echo "Enabling APIs..."
gcloud services enable container.googleapis.com containerregistry.googleapis.com storage.googleapis.com --project "${PROJECT_ID}"

# 3) Create GKE cluster if it doesn't exist
if ! gcloud container clusters describe "${CLUSTER_NAME}" --zone "${GCP_ZONE}" >/dev/null 2>&1; then
  echo "Creating GKE cluster ${CLUSTER_NAME}..."
  gcloud container clusters create "${CLUSTER_NAME}" \
    --zone "${GCP_ZONE}" \
    --num-nodes="${CLUSTER_NODE_COUNT}" \
    --machine-type="${CLUSTER_MACHINE_TYPE}" \
    --enable-ip-alias
else
  echo "Cluster ${CLUSTER_NAME} already exists — skipping creation."
fi

# 4) Get kubectl credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials "${CLUSTER_NAME}" --zone "${GCP_ZONE}"

# 5) Configure Docker to push to GCR
echo "Configuring Docker auth for GCR..."
gcloud auth configure-docker --quiet

# 6) Create GCS bucket if missing and upload model
if ! gsutil ls -b "gs://${GCS_BUCKET}" >/dev/null 2>&1; then
  echo "Creating bucket gs://${GCS_BUCKET}..."
  gsutil mb -l "${GCP_ZONE%?-?}" "gs://${GCS_BUCKET}"
else
  echo "Bucket gs://${GCS_BUCKET} already exists."
fi

if [ ! -f "${MODEL_LOCAL_PATH}" ]; then
  echo "ERROR: model file not found at ${MODEL_LOCAL_PATH}"
  echo "Put your trained model at the path above and re-run."
  exit 1
fi

echo "Uploading model to GCS..."
gsutil cp "${MODEL_LOCAL_PATH}" "gs://${GCS_BUCKET}/model.pt"
echo "Model uploaded to gs://${GCS_BUCKET}/model.pt"

# 7) Build & push Docker image for inference
echo "Building Docker image..."
docker build --pull -t "${IMAGE_REPO}:${IMAGE_TAG}" .

echo "Pushing Docker image to GCR..."
docker push "${IMAGE_REPO}:${IMAGE_TAG}"

# 8) Create kubernetes secret for pulling images (GKE usually handles this via node scopes)
# (skip if public access or already configured)
# kubectl create secret docker-registry gcr-json-key --docker-server=https://gcr.io --docker-username=_json_key --docker-password="$(cat key.json)" --docker-email=you@example.com || true

# 9) Deploy using Kubernetes manifests
echo "Deploying Kubernetes manifests..."
cd k8s

# Create namespace first
kubectl apply -f namespace.yaml

# Apply RBAC resources
kubectl apply -f rbac.yaml

# Apply ConfigMap and Secret
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# Apply PVC
kubectl apply -f pvc.yaml

# Wait for PVC to be bound
kubectl wait --for=condition=Bound pvc/mlops-artifacts-pvc -n mlops --timeout=60s

# Apply GCP-specific deployment (with init container for GCS)
kubectl apply -f deployment-gcp.yaml

# Apply GCP-specific services
kubectl apply -f service-gcp.yaml

# Apply HPA
kubectl apply -f hpa.yaml

# Wait for deployment to be ready
kubectl wait --for=condition=available --timeout=300s deployment/mlops-fastapi -n mlops

cd ..

echo "Deployment installed. Waiting for service external IP (if LoadBalancer)..."

# 10) Get service info
echo "Services:"
kubectl get svc -n mlops

# Print endpoint — if LoadBalancer, get external IP
EXTERNAL_IP=""
SVC_JSON=$(kubectl get svc mlops-fastapi-service -n mlops -o json 2>/dev/null || true)
if [ -n "$SVC_JSON" ]; then
  EXTERNAL_IP=$(echo "$SVC_JSON" | python -c "import sys, json; s=json.load(sys.stdin); \
  ip=s.get('status',{}).get('loadBalancer',{}).get('ingress',[{}])[0].get('ip') or s.get('spec',{}).get('clusterIP'); \
  print(ip if ip else '')")
fi

if [ -n "${EXTERNAL_IP}" ]; then
  echo "External IP / Cluster IP: ${EXTERNAL_IP}"
  echo "Try: curl http://${EXTERNAL_IP}/health"
  echo "Try: curl -X POST http://${EXTERNAL_IP}/predict -F \"file=@sample.png\""
else
  echo "No external IP found — if you used NodePort or your cluster is internal, run:"
  echo "  kubectl get svc -n mlops -o wide"
fi

echo "Done."
