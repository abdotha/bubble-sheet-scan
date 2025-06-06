# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m appuser

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies in stages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir torch==2.1.2+cpu torchaudio==2.1.2+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html && \
    pip install --no-cache-dir onnxruntime==1.16.3 && \
    pip install --no-cache-dir fastapi==0.109.2 uvicorn==0.27.1 python-multipart==0.0.6 && \
    pip install --no-cache-dir Pillow==10.2.0 && \
    pip install --no-cache-dir opencv-python-headless==4.9.0.80 && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories with proper permissions
RUN mkdir -p /app/static /app/templates /app/output/results /app/output/temp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Copy the application files
COPY --chown=appuser:appuser . .

# Ensure directories are writable
RUN chmod -R 777 /app/output /app/static

# Switch to non-root user
USER appuser

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8080

# Command to run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1 