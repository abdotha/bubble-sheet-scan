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
RUN useradd -m appuser && \
    mkdir -p /app/output/results /app/output/temp /app/static /app/templates && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/output /app/static

# Copy requirements first (modified version)
COPY requirements.txt .

# Create a cleaned version of requirements.txt without tts_arabic
RUN grep -v "tts_arabic" requirements.txt > cleaned_requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Install CPU-compatible versions of ML packages first
    pip install --no-cache-dir numpy==1.23.5 && \
    pip install --no-cache-dir onnxruntime==1.16.3 && \
    pip install --no-cache-dir torch==2.0.1+cpu torchaudio==2.0.2+cpu --index-url https://download.pytorch.org/whl/cpu && \
    # Install remaining requirements
    pip install --no-cache-dir -r cleaned_requirements.txt

# Copy application
COPY . .
USER appuser

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=DEBUG
ENV PYTHONPATH=/app

EXPOSE 8080

CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --log-level debug