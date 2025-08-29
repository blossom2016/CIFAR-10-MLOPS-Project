from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import torch
from torchvision import transforms
from PIL import Image
from model import build_model
import os
import logging
from datetime import datetime

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
except Exception as e:
    logger.error(f"Failed to load model from {MODEL_PATH}: {e}")
    model = None

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
    return {
        "model_loaded": 1 if model is not None else 0,
        "total_classes": len(classes),
        "model_path": MODEL_PATH
    }

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if model is None:
        return JSONResponse(
            content={"error": "Model not loaded"},
            status_code=503
        )
    
    try:
        # Load image
        image = Image.open(file.file).convert("RGB")
        x = transform(image).unsqueeze(0)

        # Prediction
        with torch.no_grad():
            preds = model(x)
            predicted_class = classes[preds.argmax(dim=1).item()]
            confidence = torch.softmax(preds, dim=1).max().item()

        logger.info(f"Prediction: {predicted_class} with confidence: {confidence:.3f}")
        
        return {
            "prediction": predicted_class,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Prediction error: {e}")
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
