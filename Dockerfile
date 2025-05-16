FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime AS builder

WORKDIR /app

# Install system dependencies required for building Python packages and audio libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    libsndfile1 \
    libasound2-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first for better caching
COPY requirements.txt .

# Install uv for faster package installation
RUN pip install uv

# Create a virtual environment and install dependencies with uv
RUN uv venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install dependencies in the correct order to avoid conflicts
# First install typing-extensions to ensure correct version for both torch and pydantic-settings
RUN uv pip install typing-extensions>=4.8.0

# Then install PyTorch
RUN uv pip install torch==2.3.0 torchaudio>=2.3.0

# Then install the rest of the packages with --no-deps for pydantic-settings
RUN grep -v "pydantic-settings\|typing-extensions\|torch\|torchaudio" requirements.txt > base_requirements.txt && \
    uv pip install -r base_requirements.txt && \
    uv pip install pydantic-settings==0.2.5 --no-deps && \
    rm base_requirements.txt

# Set environment variable for audiocraft cache
ENV AUDIOCRAFT_CACHE_DIR=/app/.cache

# Stage 2: Runtime stage (using the same base image for CUDA compatibility)
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Set environment variables for Python and audiocraft
ENV AUDIOCRAFT_CACHE_DIR=/app/.cache \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Create necessary directories
RUN mkdir -p credentials uploaded_tracks generated_tracks temp_stems .cache

# Copy application code 
COPY . .

# Verify uvicorn is installed and in PATH
RUN which uvicorn || echo "uvicorn not found in PATH"
RUN ls -la /app/venv/bin/

# Expose ports
EXPOSE 8000

# Default command for the app service (use absolute path to uvicorn)
CMD ["/app/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]