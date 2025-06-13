FROM python:3.12-slim

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
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a single layer to reduce image size
RUN pip install --upgrade pip wheel && \
    pip install -r requirements.txt && \
    pip install watchdog  # For better file watching in development

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# We're not copying the application code here for development
# It will be mounted as a volume for hot reload
# COPY . .  # This line is commented out for development

# Verify uvicorn is installed and in PATH
RUN which uvicorn || echo "uvicorn not found in PATH"

# Expose ports
EXPOSE 8000

# Command to run the application with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]