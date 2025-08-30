from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, Response
import torch
from torchvision import transforms
from PIL import Image
from model import build_model
import os
import logging
import time
from datetime import datetime
from monitoring import (
    record_prediction, get_model_metrics, get_system_metrics, 
    detect_model_drift, set_baseline_metrics, PredictionRecord,
    get_prometheus_metrics, MODEL_LOADED
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
MODEL_PATH = os.getenv("MODEL_PATH", "model.pt")
CLASSES_PATH = os.getenv("CLASSES_PATH", "artifacts/classes.txt")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Recreate the same model architecture
model = build_model(num_classes=10, pretrained=False)

# Load model if it exists
try:
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    logger.info(f"Model loaded successfully from {MODEL_PATH}")
    MODEL_LOADED.set(1)  # Set Prometheus metric
except Exception as e:
    logger.error(f"Failed to load model from {MODEL_PATH}: {e}")
    model = None
    MODEL_LOADED.set(0)  # Set Prometheus metric

# Image preprocessing
transform = transforms.Compose([
    transforms.Resize((32,32)),
    transforms.ToTensor()
])

# Class labels (CIFAR-10)
classes = ["airplane", "automobile", "bird", "cat", "deer", 
           "dog", "frog", "horse", "ship", "truck"]

app = FastAPI(
    title="CIFAR-10 Image Classifier API",
    description="A FastAPI application for CIFAR-10 image classification using PyTorch",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "CIFAR-10 Image Classifier API is running 🚀",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": model is not None
    }

@app.get("/health")
def health_check():
    """Health check endpoint for Kubernetes liveness probe"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": model is not None
    }

@app.get("/ready")
def readiness_check():
    """Readiness check endpoint for Kubernetes readiness probe"""
    if model is None:
        return JSONResponse(
            content={"status": "not ready", "reason": "Model not loaded"},
            status_code=503
        )
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": True
    }

@app.get("/metrics")
def metrics():
    """Metrics endpoint for Prometheus monitoring"""
    return Response(
        content=get_prometheus_metrics(),
        media_type="text/plain"
    )

@app.get("/monitoring/model")
def model_monitoring():
    """Get model monitoring metrics"""
    metrics = get_model_metrics()
    return {
        "model_metrics": {
            "total_predictions": metrics.total_predictions,
            "successful_predictions": metrics.successful_predictions,
            "failed_predictions": metrics.failed_predictions,
            "avg_confidence": metrics.avg_confidence,
            "avg_processing_time": metrics.avg_processing_time,
            "class_distribution": metrics.class_distribution,
            "recent_errors": metrics.recent_errors
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/monitoring/system")
def system_monitoring():
    """Get system monitoring metrics"""
    return get_system_metrics()

@app.get("/monitoring/drift")
def drift_detection():
    """Check for model drift"""
    return detect_model_drift()

@app.post("/monitoring/baseline")
def set_baseline():
    """Set baseline metrics for drift detection"""
    current_metrics = get_model_metrics()
    set_baseline_metrics(current_metrics)
    return {
        "message": "Baseline metrics set successfully",
        "baseline": {
            "avg_confidence": current_metrics.avg_confidence,
            "avg_processing_time": current_metrics.avg_processing_time,
            "class_distribution": current_metrics.class_distribution
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    start_time = time.time()
    
    if model is None:
        error_msg = "Model not loaded"
        record_prediction(PredictionRecord(
            timestamp=datetime.now(),
            predicted_class="unknown",
            confidence=0.0,
            processing_time=time.time() - start_time,
            input_size=(0, 0),
            success=False,
            error_message=error_msg
        ))
        return JSONResponse(
            content={"error": error_msg},
            status_code=503
        )
    
    try:
        # Load image
        image = Image.open(file.file).convert("RGB")
        input_size = image.size
        x = transform(image).unsqueeze(0)

        # Prediction
        with torch.no_grad():
            preds = model(x)
            predicted_class = classes[preds.argmax(dim=1).item()]
            confidence = torch.softmax(preds, dim=1).max().item()

        processing_time = time.time() - start_time
        logger.info(f"Prediction: {predicted_class} with confidence: {confidence:.3f}")
        
        # Record prediction for monitoring
        record_prediction(PredictionRecord(
            timestamp=datetime.now(),
            predicted_class=predicted_class,
            confidence=confidence,
            processing_time=processing_time,
            input_size=input_size,
            success=True
        ))
        
        return {
            "prediction": predicted_class,
            "confidence": confidence,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Prediction error: {e}")
        
        # Record failed prediction for monitoring
        record_prediction(PredictionRecord(
            timestamp=datetime.now(),
            predicted_class="unknown",
            confidence=0.0,
            processing_time=processing_time,
            input_size=(0, 0),
            success=False,
            error_message=str(e)
        ))
        
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.get("/classes")
def get_classes():
    """Get list of available classes"""
    return {
        "classes": classes,
        "count": len(classes)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
