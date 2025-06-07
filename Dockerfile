FROM python:3.10-slim

WORKDIR /app

# 1. Install essential system dependencies
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

# 4. Install base packages first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy==1.21.6

# 5. Install packages one by one from requirements.txt
RUN while read requirement; do \
      echo "Installing $requirement..."; \
      pip install --no-cache-dir $requirement || \
      { echo "Failed to install $requirement - trying with --ignore-installed"; \
        pip install --no-cache-dir --ignore-installed $requirement || \
        echo "Skipping $requirement"; }; \
    done < requirements.txt

# 6. Verify critical packages
RUN pip list && \
    python -c "import numpy; print(f'numpy version: {numpy.__version__}')"

# 7. Copy application code
COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]