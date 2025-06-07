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

# 3. Install Python toolchain first
RUN python -m pip install --no-cache-dir --upgrade pip==23.1.2 setuptools==67.7.2 wheel==0.40.0

# 4. Install base packages individually with retries
RUN pip install --no-cache-dir numpy==1.21.6 || \
    pip install --no-cache-dir numpy==1.21.6 --ignore-installed

RUN pip install --no-cache-dir opencv-python-headless==4.5.5.64 || \
    { apt-get update && apt-get install -y libopencv-dev && \
      pip install --no-cache-dir opencv-python-headless==4.5.5.64; }

RUN pip install --no-cache-dir torch==1.10.0+cpu torchvision==0.11.1+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html || \
    pip install --no-cache-dir torch==1.9.0+cpu torchvision==0.10.0+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html

# 5. Install remaining requirements with error handling
COPY requirements.txt .
RUN cat requirements.txt | while read package; do \
      echo "Installing $package..."; \
      pip install --no-cache-dir "$package" || \
      { echo "Failed to install $package, trying with --ignore-installed"; \
        pip install --no-cache-dir --ignore-installed "$package" || \
        echo "Skipping $package"; }; \
    done

# 6. Verification stage
RUN python -c "import numpy; import cv2; import torch; print(f'Versions: numpy={numpy.__version__}, opencv={cv2.__version__}, torch={torch.__version__}')"

# 7. Copy application
COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]