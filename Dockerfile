FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m appuser

# Create and set permissions for /tmp directories
RUN mkdir -p /tmp/output/results /tmp/output/temp && \
    chown -R appuser:appuser /tmp/output && \
    chmod -R 777 /tmp/output

# Copy requirements
COPY requirements.txt .

# Install Python dependencies in optimized order
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Install numpy first as it's a common dependency
    pip install --no-cache-dir numpy==2.2.4 && \
    # Install PyTorch with CPU-only version
    pip install --no-cache-dir torch==2.6.0+cpu torchaudio==2.6.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu && \
    # Replace onnxruntime-gpu with CPU version
    pip install --no-cache-dir onnxruntime==1.16.3 && \
    # Install remaining requirements
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set permissions for application files
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=DEBUG
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug"]