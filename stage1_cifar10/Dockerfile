# Start from an official PyTorch image with CUDA support (for GPU training)
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables to prevent DataLoader worker issues in Docker
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

# By default, run training
CMD ["python", "train.py", "--epochs", "5", "--batch-size", "64", "--out-dir", "artifacts"]
