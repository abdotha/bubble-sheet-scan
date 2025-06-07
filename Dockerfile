FROM python:3.9-slim

WORKDIR /app

# 1. Install system dependencies including build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Create directories with proper permissions
RUN mkdir -p /app/output/results /app/output/temp /app/static /app/templates && \
    chmod -R 777 /app/output /app/static

# 3. Copy requirements first
COPY requirements.txt .

# 4. Install Python dependencies with error handling
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy && \
    { pip install --no-cache-dir -r requirements.txt || \
      { echo "Primary installation failed, trying alternative approach..." && \
        pip install --no-cache-dir --ignore-installed -r requirements.txt; }; }

# 5. Verify critical packages
RUN pip list && \
    python -c "import numpy, torch, cv2; print(f'Versions: numpy={numpy.__version__}, torch={torch.__version__}, opencv={cv2.__version__}')"

# 6. Copy application code
COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]