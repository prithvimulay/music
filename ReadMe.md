## PROJECT TERMINATED:
   lack of infra, need gpu to compute, usecase is very limited

# Music Generation API

A FastAPI-based service for AI music generation using Replicate's MusicGen model.

tester@gmail.com pass@123 --user_id = 4
2June -- proj_id = 5

## Prerequisites

- Docker and Docker Compose
- Replicate API token (get one from [replicate.com](https://replicate.com))
- Python 3.9+ (for local development)

## Environment Setup

1. Clone this repository
2. Copy the `.env.example` to `.env` (if it doesn't exist already)
3. Update the `.env` file with your Replicate API token:
   ```
   REPLICATE_API_TOKEN=your_replicate_token_here
   REPLICATE_MODEL_ID=meta/musicgen:7a76a8258b23fae65c5a22debb8841d1d7e816b75c2f24218cd2bd8573787906
   MUSICGEN_MODEL_ID=facebook/musicgen-small
   ```

## Starting the Services

### Using Docker (Recommended)

Start all services with a single command:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis for Celery
- FastAPI application
- Celery worker
- Flower (Celery monitoring)

To check if all services are running:

```bash
docker-compose ps
```

### Verify Service Status

Check API service logs:
```bash
docker-compose logs -f api
```

Check Celery worker logs:
```bash
docker-compose logs -f celery_worker
```

### Testing the Replicate API Connection

You can test if your Replicate API token is working correctly by using the test endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/test/test-replicate-connection/
```

Or test the full audio generation:

#### For Windows Command Prompt:
```bash
curl -X POST http://localhost:8000/api/v1/test/test-generate/ -H "Content-Type: application/json" -d "{\"prompt\": \"Upbeat electronic music\", \"duration\": 5}"
```

#### For PowerShell:
```powershell
Invoke-WebRequest -Uri http://localhost:8000/api/v1/test/test-generate/ -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"prompt": "Upbeat electronic music", "duration": 5}'
```

#### For Linux/Mac/Git Bash:
```bash
curl -X POST http://localhost:8000/api/v1/test/test-generate/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Upbeat electronic music", "duration": 5}'
```

### Checking Environment Variables

To verify environment variables in containers:

```bash
# Check Replicate API token (masked for security)
docker-compose exec api bash -c 'echo ${REPLICATE_API_TOKEN:0:4}...${REPLICATE_API_TOKEN:(-4)}'

# Check Replicate model ID
docker-compose exec api bash -c 'echo $REPLICATE_MODEL_ID'

# Check MusicGen model ID
docker-compose exec api bash -c 'echo $MUSICGEN_MODEL_ID'
```

## Stopping Services

Stop all services:

```bash
docker-compose down
```

To stop and remove volumes (will delete database data):

```bash
docker-compose down -v
```

## Local Development

For local development without Docker:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export REPLICATE_API_TOKEN=your_token_here
   export RUNNING_LOCALLY=true
   ```

3. Run the API:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Run Celery worker (in a separate terminal):
   ```bash
   celery -A app.celeryworker.worker worker -l info
   ```

## API Documentation

Once the API is running, you can access the interactive documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

For more details, see [API_DOCUMENTATION.md](./API_DOCUMENTATION.md).