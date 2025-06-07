FROM python:3.9-slim

WORKDIR /app

# 1. Install comprehensive system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Create directories with proper permissions
RUN mkdir -p /app/output/results /app/output/temp /app/static /app/templates && \
    chmod -R 777 /app/output /app/static

# 3. Install Python dependencies in controlled stages
COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip==21.3.1 setuptools==59.6.0 wheel==0.37.0 && \
    pip install --no-cache-dir numpy==1.21.6 && \
    pip install --no-cache-dir opencv-python-headless==4.5.5.64 && \
    pip install --no-cache-dir torch==1.10.0+cpu torchvision==0.11.1+cpu -f https://download.pytorch.org/whl/torch_stable.html && \
    pip install --no-cache-dir -r requirements.txt

# 4. Verification stage
RUN python -c "import numpy; import cv2; import torch; print(f'Versions: numpy={numpy.__version__}, opencv={cv2.__version__}, torch={torch.__version__}')"

# 5. Copy application
COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]