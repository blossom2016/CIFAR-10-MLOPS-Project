#!/usr/bin/env python3
"""
Test script for monitoring functionality
Generates test data and validates monitoring endpoints
"""

import requests
import time
import json
import random
from PIL import Image
import numpy as np
import io
import os

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_IMAGES_DIR = "test_images"
NUM_REQUESTS = 50

def create_test_image():
    """Create a random test image"""
    # Create a random 32x32 RGB image
    img_array = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes

def test_health_endpoints():
    """Test health and monitoring endpoints"""
    print("🔍 Testing health endpoints...")
    
    endpoints = [
        "/",
        "/health",
        "/ready",
        "/metrics",
        "/monitoring/model",
        "/monitoring/system",
        "/monitoring/drift"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}")
            print(f"  ✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(f"     Response: {response.text[:100]}...")
        except Exception as e:
            print(f"  ❌ {endpoint}: Error - {e}")

def test_prediction_endpoint():
    """Test prediction endpoint with monitoring"""
    print("\n🚀 Testing prediction endpoint...")
    
    success_count = 0
    error_count = 0
    
    for i in range(NUM_REQUESTS):
        try:
            # Create test image
            img_bytes = create_test_image()
            
            # Make prediction request
            files = {'file': ('test_image.png', img_bytes, 'image/png')}
            start_time = time.time()
            
            response = requests.post(f"{API_BASE_URL}/predict", files=files)
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Request {i+1}: {result['prediction']} (confidence: {result['confidence']:.3f}, time: {processing_time:.3f}s)")
                success_count += 1
            else:
                print(f"  ❌ Request {i+1}: Error {response.status_code} - {response.text}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ Request {i+1}: Exception - {e}")
            error_count += 1
        
        # Add some delay between requests
        time.sleep(0.1)
    
    print(f"\n📊 Prediction Test Results:")
    print(f"  Total requests: {NUM_REQUESTS}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {error_count}")
    print(f"  Success rate: {success_count/NUM_REQUESTS*100:.1f}%")

def test_model_drift():
    """Test model drift detection"""
    print("\n📈 Testing model drift detection...")
    
    try:
        # Set baseline
        print("  Setting baseline metrics...")
        response = requests.post(f"{API_BASE_URL}/monitoring/baseline")
        if response.status_code == 200:
            baseline = response.json()
            print(f"  ✅ Baseline set: {baseline['baseline']}")
        
        # Generate some predictions to establish baseline
        print("  Generating baseline predictions...")
        for i in range(10):
            img_bytes = create_test_image()
            files = {'file': ('test_image.png', img_bytes, 'image/png')}
            requests.post(f"{API_BASE_URL}/predict", files=files)
            time.sleep(0.1)
        
        # Check for drift
        print("  Checking for model drift...")
        response = requests.get(f"{API_BASE_URL}/monitoring/drift")
        if response.status_code == 200:
            drift_info = response.json()
            print(f"  ✅ Drift detection: {drift_info}")
        else:
            print(f"  ❌ Drift detection failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Drift test failed: {e}")

def test_metrics_endpoint():
    """Test Prometheus metrics endpoint"""
    print("\n📊 Testing Prometheus metrics...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/metrics")
        if response.status_code == 200:
            metrics = response.text
            print("  ✅ Metrics endpoint working")
            
            # Check for key metrics
            key_metrics = [
                'cifar10_predictions_total',
                'cifar10_prediction_duration_seconds',
                'cifar10_prediction_confidence',
                'cifar10_model_loaded',
                'cifar10_system_memory_bytes',
                'cifar10_system_cpu_percent'
            ]
            
            for metric in key_metrics:
                if metric in metrics:
                    print(f"    ✅ Found metric: {metric}")
                else:
                    print(f"    ❌ Missing metric: {metric}")
        else:
            print(f"  ❌ Metrics endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Metrics test failed: {e}")

def main():
    """Main test function"""
    print("🧪 CIFAR-10 Monitoring Test Suite")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ API is not healthy: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API at {API_BASE_URL}: {e}")
        print("Make sure the API is running with: python app.py")
        return
    
    print("✅ API is running and healthy")
    
    # Run tests
    test_health_endpoints()
    test_prediction_endpoint()
    test_model_drift()
    test_metrics_endpoint()
    
    print("\n🎉 Monitoring test suite completed!")
    print("\n📋 Next steps:")
    print("  1. Check Prometheus metrics at: http://localhost:8000/metrics")
    print("  2. View model monitoring at: http://localhost:8000/monitoring/model")
    print("  3. Check system metrics at: http://localhost:8000/monitoring/system")
    print("  4. Monitor drift detection at: http://localhost:8000/monitoring/drift")

if __name__ == "__main__":
    main()
