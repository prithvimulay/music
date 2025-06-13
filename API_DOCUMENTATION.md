# Music Generation API Documentation

## Overview

This API provides endpoints for generating music with separated stems using the Replicate API for MusicGen models, and for mixing those stems with volume adjustments. The API uses FastAPI, Celery with Redis for asynchronous task processing, and Google Drive for file storage.

## Authentication

All endpoints require authentication. Authentication is handled via JWT tokens.

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### Generated Music

#### Generate Music with Stems

```
POST /generated-music/
```

Generates music with separated stems (bass, drums, other) based on a text prompt.

**Request Body:**

```json
{
  "prompt": "Upbeat electronic dance music with a strong bass line",
  "duration": 30,
  "melody_audio_id": "optional_gdrive_id_for_melody_conditioning",
  "proj_id": 1
}
```

**Response:**

```json
{
  "id": 1,
  "prompt": "Upbeat electronic dance music with a strong bass line",
  "duration": 30,
  "status": "pending",
  "progress": 0,
  "created_at": "2025-06-03T10:00:00.000Z",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab"
}
```

#### Get Generated Music

```
GET /generated-music/{generated_music_id}
```

Retrieves details about a specific generated music item.

**Response:**

```json
{
  "id": 1,
  "prompt": "Upbeat electronic dance music with a strong bass line",
  "duration": 30,
  "status": "completed",
  "progress": 100,
  "created_at": "2025-06-03T10:00:00.000Z",
  "completed_at": "2025-06-03T10:02:00.000Z",
  "stems": [
    {
      "id": 1,
      "stem_type": "bass",
      "filename": "gen_1_bass.wav",
      "gdrive_file_id": "gdrive_id_for_bass_stem",
      "status": "completed"
    },
    {
      "id": 2,
      "stem_type": "drums",
      "filename": "gen_1_drums.wav",
      "gdrive_file_id": "gdrive_id_for_drums_stem",
      "status": "completed"
    },
    {
      "id": 3,
      "stem_type": "other",
      "filename": "gen_1_other.wav",
      "gdrive_file_id": "gdrive_id_for_other_stem",
      "status": "completed"
    }
  ]
}
```

#### List Generated Music

```
GET /generated-music/
```

Lists all generated music items for the current user.

**Query Parameters:**

- `proj_id` (optional): Filter by project ID
- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Maximum number of items to return (default: 100)

**Response:**

```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "prompt": "Upbeat electronic dance music with a strong bass line",
      "duration": 30,
      "status": "completed",
      "progress": 100,
      "created_at": "2025-06-03T10:00:00.000Z"
    }
  ]
}
```

### Mixed Tracks

#### Create Mixed Track

```
POST /mixed-tracks/
```

Creates a mixed track by combining selected stems with optional volume adjustments.

**Request Body:**

```json
{
  "generated_music_id": 1,
  "selected_stems": ["bass", "drums", "other"],
  "volume_levels": {
    "bass": 1.0,
    "drums": 0.8,
    "other": 0.9
  },
  "proj_id": 1
}
```

**Response:**

```json
{
  "id": 1,
  "generated_music_id": 1,
  "selected_stems": ["bass", "drums", "other"],
  "volume_levels": {
    "bass": 1.0,
    "drums": 0.8,
    "other": 0.9
  },
  "status": "pending",
  "progress": 0,
  "created_at": "2025-06-03T11:00:00.000Z",
  "task_id": "b2c3d4e5-f6g7-8901-bcde-2345678901cd"
}
```

#### Get Mixed Track

```
GET /mixed-tracks/{mixed_track_id}
```

Retrieves details about a specific mixed track.

**Response:**

```json
{
  "id": 1,
  "generated_music_id": 1,
  "selected_stems": ["bass", "drums", "other"],
  "volume_levels": {
    "bass": 1.0,
    "drums": 0.8,
    "other": 0.9
  },
  "status": "completed",
  "progress": 100,
  "created_at": "2025-06-03T11:00:00.000Z",
  "completed_at": "2025-06-03T11:01:00.000Z",
  "gdrive_file_id": "gdrive_id_for_mixed_track",
  "filename": "mixed_1.wav",
  "file_size": 12345678
}
```

#### List Mixed Tracks

```
GET /mixed-tracks/
```

Lists all mixed tracks for the current user.

**Query Parameters:**

- `proj_id` (optional): Filter by project ID
- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Maximum number of items to return (default: 100)

**Response:**

```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "generated_music_id": 1,
      "status": "completed",
      "progress": 100,
      "created_at": "2025-06-03T11:00:00.000Z",
      "filename": "mixed_1.wav"
    }
  ]
}
```

### Test Endpoints

#### Test Replicate Connection

```
POST /api/v1/test/test-replicate-connection/
```

Tests if the Replicate API token is valid and the model can be accessed without generating full audio. This endpoint is useful for verifying API connectivity and model access.

**Request Body:**
None required

**Response:**
```json
{
  "status": "success",
  "message": "Replicate API connection and model access successful",
  "details": {
    "client_version": "0.18.1",
    "model_id": "meta/musicgen:7a76a8258b23fae65c5a22debb8841d1d7e816b75c2f24218cd2bd8573787906",
    "test_output_url": "https://replicate.delivery/pbxt/example_url"
  }
}
```

#### Test Generate Audio

```
POST /api/v1/test/test-generate/
```

Tests the full audio generation pipeline using the Replicate API.

**Request Body:**
```json
{
  "prompt": "Upbeat electronic dance music",
  "duration": 5
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Audio generated successfully",
  "audio_data": "base64_encoded_audio_data",
  "audio_url": "https://replicate.delivery/pbxt/example_url"
}
```

## Removed Endpoints

The following endpoints have been removed as part of the transition from the Fusion workflow to the new Replicate API-based approach:

### Fusion (Removed)

- `POST /fusion/` - Create a new fusion
- `GET /fusion/{fusion_id}` - Get fusion details
- `GET /fusion/` - List fusions
- `POST /fusion/{fusion_id}/prepare-prompt` - Prepare prompt for fusion
- `POST /fusion/{fusion_id}/generate` - Generate fusion

These endpoints have been replaced by the new Generated Music and Mixed Tracks endpoints, which provide a more efficient and scalable approach to AI music generation using the Replicate API.

## Environment Variables

The following environment variables are required for the API to function correctly:

- `REPLICATE_API_TOKEN`: API token for the Replicate API
- `REPLICATE_MODEL_ID`: Model ID for the MusicGen model on Replicate
- `MUSICGEN_MODEL_ID`: Model ID for backward compatibility
- Database configuration variables (e.g., `POSTGRES_USER`, `POSTGRES_PASSWORD`, etc.)
- Redis configuration variables for Celery
- Google Drive API credentials

## Error Handling

All endpoints return appropriate HTTP status codes and error messages in case of failure:

- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

Error responses include a JSON object with an `error` field containing a description of the error.
