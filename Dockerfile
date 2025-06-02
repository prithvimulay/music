FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploaded_tracks /app/generated_tracks /app/temp_stems /app/.cache && \
    chmod -R 777 /app/uploaded_tracks /app/generated_tracks /app/temp_stems /app/.cache

# Copy requirements.txt first for better caching
COPY requirements.txt .

# Install system dependencies required for audio processing
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    libsndfile1 \
    libasound2-dev \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a single layer to reduce image size
# First install critical packages that need specific versions
RUN pip install --upgrade pip wheel && \
    pip install typing-extensions>=4.8.0 && \
    pip install torch==2.2.0 torchaudio==2.2.0 && \
    pip install huggingface-hub>=0.19.0 regex>=2023.0.0 safetensors>=0.3.1 tokenizers>=0.15.0 einops>=0.7.0 psutil && \
    pip install -r requirements.txt

# Install packages that need --no-deps in a separate layer
# This is kept separate to avoid dependency conflicts
RUN pip install transformers==4.35.2 --no-deps && \
    pip install accelerate==0.24.1 --no-deps && \
    pip install audiocraft==1.0.0 --no-deps

# Set environment variables for Python and audiocraft
ENV AUDIOCRAFT_CACHE_DIR=/app/.cache \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Copy application code 
COPY . .

# Verify uvicorn is installed and in PATH
RUN which uvicorn || echo "uvicorn not found in PATH"

# Expose ports
EXPOSE 8000

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]