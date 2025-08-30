import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import threading
import json
import os
from dataclasses import dataclass, asdict
import numpy as np
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
import psutil

logger = logging.getLogger(__name__)

# Prometheus metrics
PREDICTION_COUNTER = Counter('cifar10_predictions_total', 'Total number of predictions', ['class', 'status'])
PREDICTION_DURATION = Histogram('cifar10_prediction_duration_seconds', 'Prediction duration in seconds')
CONFIDENCE_HISTOGRAM = Histogram('cifar10_prediction_confidence', 'Prediction confidence scores')
MODEL_LOADED = Gauge('cifar10_model_loaded', 'Model loaded status (1=loaded, 0=not_loaded)')
REQUEST_DURATION = Histogram('cifar10_request_duration_seconds', 'Request duration in seconds', ['endpoint'])
ERROR_COUNTER = Counter('cifar10_errors_total', 'Total number of errors', ['error_type'])
SYSTEM_MEMORY = Gauge('cifar10_system_memory_bytes', 'System memory usage in bytes')
SYSTEM_CPU = Gauge('cifar10_system_cpu_percent', 'System CPU usage percentage')

@dataclass
class PredictionRecord:
    """Record for storing prediction data"""
    timestamp: datetime
    predicted_class: str
    confidence: float
    processing_time: float
    input_size: tuple
    success: bool
    error_message: Optional[str] = None

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    total_predictions: int = 0
    successful_predictions: int = 0
    failed_predictions: int = 0
    avg_confidence: float = 0.0
    avg_processing_time: float = 0.0
    class_distribution: Dict[str, int] = None
    recent_errors: List[str] = None
    
    def __post_init__(self):
        if self.class_distribution is None:
            self.class_distribution = defaultdict(int)
        if self.recent_errors is None:
            self.recent_errors = []

class ModelMonitor:
    """Model monitoring and drift detection"""
    
    def __init__(self, window_size: int = 1000, drift_threshold: float = 0.1):
        self.window_size = window_size
        self.drift_threshold = drift_threshold
        self.predictions_history = deque(maxlen=window_size)
        self.confidence_history = deque(maxlen=window_size)
        self.processing_times = deque(maxlen=window_size)
        self.class_distribution_history = deque(maxlen=window_size)
        self.baseline_metrics = None
        self.lock = threading.Lock()
        
    def record_prediction(self, prediction: PredictionRecord):
        """Record a prediction for monitoring"""
        with self.lock:
            self.predictions_history.append(prediction)
            self.confidence_history.append(prediction.confidence)
            self.processing_times.append(prediction.processing_time)
            
            # Update class distribution
            current_dist = defaultdict(int)
            for pred in self.predictions_history:
                current_dist[pred.predicted_class] += 1
            self.class_distribution_history.append(dict(current_dist))
            
            # Update Prometheus metrics
            if prediction.success:
                PREDICTION_COUNTER.labels(class=prediction.predicted_class, status='success').inc()
            else:
                PREDICTION_COUNTER.labels(class=prediction.predicted_class, status='error').inc()
                ERROR_COUNTER.labels(error_type='prediction_error').inc()
            
            CONFIDENCE_HISTOGRAM.observe(prediction.confidence)
            PREDICTION_DURATION.observe(prediction.processing_time)
    
    def set_baseline(self, baseline_metrics: ModelMetrics):
        """Set baseline metrics for drift detection"""
        self.baseline_metrics = baseline_metrics
    
    def detect_drift(self) -> Dict[str, Any]:
        """Detect model drift based on recent predictions"""
        if len(self.predictions_history) < 50:  # Need minimum data
            return {"drift_detected": False, "reason": "Insufficient data"}
        
        with self.lock:
            recent_confidences = list(self.confidence_history)[-100:]
            recent_processing_times = list(self.processing_times)[-100:]
            
            # Confidence drift
            avg_confidence = np.mean(recent_confidences)
            confidence_drift = False
            if self.baseline_metrics and abs(avg_confidence - self.baseline_metrics.avg_confidence) > self.drift_threshold:
                confidence_drift = True
            
            # Processing time drift
            avg_processing_time = np.mean(recent_processing_times)
            processing_drift = False
            if self.baseline_metrics and abs(avg_processing_time - self.baseline_metrics.avg_processing_time) > self.drift_threshold:
                processing_drift = True
            
            # Class distribution drift
            class_drift = False
            if len(self.class_distribution_history) > 0:
                recent_dist = self.class_distribution_history[-1]
                if self.baseline_metrics and self.baseline_metrics.class_distribution:
                    # Simple drift detection based on major class changes
                    baseline_total = sum(self.baseline_metrics.class_distribution.values())
                    recent_total = sum(recent_dist.values())
                    if baseline_total > 0 and recent_total > 0:
                        for class_name in recent_dist:
                            baseline_ratio = self.baseline_metrics.class_distribution.get(class_name, 0) / baseline_total
                            recent_ratio = recent_dist[class_name] / recent_total
                            if abs(baseline_ratio - recent_ratio) > self.drift_threshold:
                                class_drift = True
                                break
            
            drift_detected = confidence_drift or processing_drift or class_drift
            
            return {
                "drift_detected": drift_detected,
                "confidence_drift": confidence_drift,
                "processing_drift": processing_drift,
                "class_drift": class_drift,
                "current_avg_confidence": avg_confidence,
                "current_avg_processing_time": avg_processing_time,
                "baseline_avg_confidence": self.baseline_metrics.avg_confidence if self.baseline_metrics else None,
                "baseline_avg_processing_time": self.baseline_metrics.avg_processing_time if self.baseline_metrics else None,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_metrics(self) -> ModelMetrics:
        """Get current model metrics"""
        with self.lock:
            if not self.predictions_history:
                return ModelMetrics()
            
            predictions = list(self.predictions_history)
            successful = [p for p in predictions if p.success]
            failed = [p for p in predictions if not p.success]
            
            avg_confidence = np.mean([p.confidence for p in successful]) if successful else 0.0
            avg_processing_time = np.mean([p.processing_time for p in predictions]) if predictions else 0.0
            
            # Class distribution
            class_dist = defaultdict(int)
            for pred in predictions:
                class_dist[pred.predicted_class] += 1
            
            # Recent errors
            recent_errors = [p.error_message for p in failed[-10:] if p.error_message]
            
            return ModelMetrics(
                total_predictions=len(predictions),
                successful_predictions=len(successful),
                failed_predictions=len(failed),
                avg_confidence=avg_confidence,
                avg_processing_time=avg_processing_time,
                class_distribution=dict(class_dist),
                recent_errors=recent_errors
            )

class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self):
        self.start_time = datetime.now()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Update Prometheus metrics
            SYSTEM_MEMORY.set(memory.used)
            SYSTEM_CPU.set(cpu_percent)
            
            return {
                "memory_used_bytes": memory.used,
                "memory_total_bytes": memory.total,
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e)}

class MonitoringMiddleware:
    """FastAPI middleware for request monitoring"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            request = Request(scope, receive)
            
            # Process request
            await self.app(scope, receive, send)
            
            # Record metrics
            duration = time.time() - start_time
            endpoint = request.url.path
            REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)

# Global monitoring instances
model_monitor = ModelMonitor()
system_monitor = SystemMonitor()

def get_prometheus_metrics():
    """Get Prometheus metrics"""
    return generate_latest()

def record_prediction(prediction: PredictionRecord):
    """Record a prediction for monitoring"""
    model_monitor.record_prediction(prediction)

def get_model_metrics() -> ModelMetrics:
    """Get current model metrics"""
    return model_monitor.get_metrics()

def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics"""
    return system_monitor.get_system_metrics()

def detect_model_drift() -> Dict[str, Any]:
    """Detect model drift"""
    return model_monitor.detect_drift()

def set_baseline_metrics(baseline: ModelMetrics):
    """Set baseline metrics for drift detection"""
    model_monitor.set_baseline(baseline)
