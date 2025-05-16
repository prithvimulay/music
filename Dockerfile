FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime AS builder

WORKDIR /app

# Install system dependencies required for building Python packages and audio libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    libsndfile1 \
    libasound2-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy requirements.txt first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN uv venv .venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install --no-cache-dir -r requirements.txt

# Pre-download MusicGen model
ENV AUDIOCRAFT_CACHE_DIR=/app/.cache
RUN python -c "from audiocraft.models import MusicGen; MusicGen.get_pretrained('facebook/musicgen-small')"

# Stage 2: Runtime stage (using the same base image for simplicity and CUDA)
FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime

WORKDIR /app

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/.cache /app/.cache

# Set environment variables for Python and audiocraft
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    AUDIOCRAFT_CACHE_DIR=/app/.cache

# Copy application code 
COPY . .

RUN mkdir -p credentials uploaded_tracks generated_tracks temp_stems

# Expose ports
EXPOSE 8000

# Default command for the app service (uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]