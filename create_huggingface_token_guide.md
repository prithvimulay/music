# Hugging Face Token Setup Guide

## Error: Insufficient Permissions

If you're seeing the following error:
```
API request failed with status 403: {"error":"This authentication method does not have sufficient permissions to call Inference Providers on behalf of user ppm23"}
```

This means your Hugging Face token doesn't have the necessary permissions to use the Inference API.

## How to Fix It

1. **Go to Hugging Face Settings**:
   - Visit [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Sign in if you haven't already

2. **Create a New Token**:
   - Click "New Token"
   - Give it a name like "MusicGenAPI"
   - **IMPORTANT**: Select "Write" permission (not just "Read")
   - Click "Generate a token"

3. **Copy Your New Token**:
   - Copy the generated token (you won't be able to see it again)

4. **Update Your .env File**:
   - Run the `update_huggingface_token.ps1` script:
     ```
     .\update_huggingface_token.ps1
     ```
   - Paste your new token when prompted

5. **Restart Docker Containers**:
   ```
   docker-compose down
   docker-compose up -d
   ```

## Additional Requirements

To use the Hugging Face Inference API for MusicGen:

1. **Accept Model Terms**:
   - Visit [https://huggingface.co/facebook/musicgen-stereo-small](https://huggingface.co/facebook/musicgen-stereo-small)
   - Click "Agree and access repository" if prompted

2. **Pro Subscription**:
   - Some models require a Hugging Face Pro subscription
   - Check if you need to upgrade at [https://huggingface.co/pricing](https://huggingface.co/pricing)

## Testing Your Token

After updating your token, you can test it by:

1. Going to the Swagger UI: http://localhost:8000/docs
2. Using the `/api/v1/test-musicgen/test-connection` endpoint
3. This will verify if your token has the correct permissions
