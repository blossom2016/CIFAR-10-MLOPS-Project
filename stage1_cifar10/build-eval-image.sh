#!/bin/bash

# Build and push evaluation Docker image
# This script builds the evaluation image using Dockerfile.eval

set -e

# GCP Configuration
PROJECT_ID="${PROJECT_ID:-my-mlops-project2}"
GCR_REGION="${GCR_REGION:-gcr.io}"
IMAGE_REPO="${IMAGE_REPO:-${GCR_REGION}/${PROJECT_ID}/vision-inference}"
IMAGE_TAG="${IMAGE_TAG:-eval}"

echo "Building evaluation Docker image..."
echo "Project: ${PROJECT_ID}"
echo "Image: ${IMAGE_REPO}:${IMAGE_TAG}"
echo

# Build the evaluation image
docker build -f Dockerfile.eval -t "${IMAGE_REPO}:${IMAGE_TAG}" .

echo "Pushing evaluation image to GCR..."
docker push "${IMAGE_REPO}:${IMAGE_TAG}"

echo "✅ Evaluation image built and pushed successfully!"
echo "Image: ${IMAGE_REPO}:${IMAGE_TAG}"
echo
echo "To run evaluation job:"
echo "  kubectl apply -f k8s/job-eval.yaml"
echo
echo "To check job status:"
echo "  kubectl get jobs -n mlops"
echo "  kubectl logs job/mlops-evaluation-job -n mlops" 