"""
Test endpoint for MusicGen model generation via Replicate API.
"""
import logging
import os
import base64
import tempfile
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.music_generation import get_musicgen_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str
    duration: int = 5


class GenerateResponse(BaseModel):
    status: str
    message: str
    audio_data: Optional[str] = None
    audio_url: Optional[str] = None
    details: Optional[Dict] = None


@router.post("/test-generate/", response_model=GenerateResponse)
async def test_generate(request: GenerateRequest):
    """
    Test if the Replicate API can generate audio properly.
    """
    try:
        # Get service
        service = get_musicgen_service()
        
        if not service.replicate_token:
            return GenerateResponse(
                status="error",
                message="Replicate API token not configured",
                details={"error": "Set REPLICATE_API_TOKEN in .env"}
            )
        
        logger.info(f"Testing Replicate audio generation with prompt: {request.prompt}")
        
        try:
            import replicate
        except ImportError:
            return GenerateResponse(
                status="error",
                message="Replicate Python package not installed",
                details={"error": "Install with 'pip install replicate'"}
            )
        
        # Set the API token
        os.environ["REPLICATE_API_TOKEN"] = service.replicate_token
        
        # Prepare the input parameters
        input_params = {
            "prompt": request.prompt,
            "duration": request.duration,
            "output_format": "wav",
            "normalization_strategy": "peak",
            "temperature": 1.0,
            "classifier_free_guidance": 3.0
        }
        
        # Log request details
        logger.info(f"Using Replicate model: {service.replicate_model_id}")
        
        # Run the model
        output = replicate.run(
            service.replicate_model_id,
            input=input_params
        )
        
        # The output should be a URL to the generated audio
        if output and isinstance(output, list) and len(output) > 0:
            audio_url = output[0]
            logger.info(f"Generated audio URL: {audio_url}")
            
            # Create a temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "test_output.wav")
                
                # Download the audio file
                import requests
                response = requests.get(audio_url)
                if response.status_code == 200:
                    # Save the audio file
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    
                    # Read and encode the audio file
                    with open(output_path, "rb") as f:
                        audio_data = base64.b64encode(f.read()).decode("utf-8")
                    
                    return GenerateResponse(
                        status="success",
                        message="Audio generated successfully",
                        audio_data=audio_data,
                        audio_url=audio_url
                    )
                else:
                    return GenerateResponse(
                        status="error",
                        message=f"Failed to download audio file: {response.status_code}",
                        audio_url=audio_url
                    )
        else:
            return GenerateResponse(
                status="error",
                message=f"Unexpected output format from Replicate",
                details={"output": output}
            )
                
    except Exception as e:
        logger.error(f"Error generating audio with Replicate: {str(e)}")
        return GenerateResponse(
            status="error",
            message=f"Failed to generate audio: {str(e)}",
            details={"error_type": type(e).__name__, "error_traceback": str(e)}
        )


@router.post("/test-replicate-connection/", response_model=GenerateResponse)
async def test_replicate_connection():
    """
    Test if the Replicate API token is valid and the model can be accessed.
    This endpoint doesn't generate audio, it just verifies API access.
    """
    try:
        # Get service
        service = get_musicgen_service()
        
        if not service.replicate_token:
            logger.error("Replicate API token not configured")
            return GenerateResponse(
                status="error",
                message="Replicate API token not configured",
                details={"error": "Set REPLICATE_API_TOKEN in .env"}
            )
        
        logger.info(f"Testing Replicate API connection with token: {service.replicate_token[:4]}...{service.replicate_token[-4:]}")
        
        try:
            import replicate
        except ImportError:
            logger.error("Replicate Python package not installed")
            return GenerateResponse(
                status="error",
                message="Replicate Python package not installed",
                details={"error": "Install with 'pip install replicate'"}
            )
        
        # Set the API token
        os.environ["REPLICATE_API_TOKEN"] = service.replicate_token
        
        # Test connection by getting model info
        try:
            # Get the package version instead of using version_info()
            import pkg_resources
            version = pkg_resources.get_distribution("replicate").version
            logger.info(f"Replicate Python package version: {version}")
            
            # Now check if we can access the model
            logger.info(f"Checking access to model: {service.replicate_model_id}")
            
            # Make a minimal prediction with a dummy prompt to check model access
            # Using minimal duration to reduce computation time
            test_output = replicate.run(
                service.replicate_model_id,
                input={
                    "prompt": "Test connection",
                    "duration": 1,  # Minimum duration
                    "output_format": "wav",
                }
            )
            
            if test_output and isinstance(test_output, list) and len(test_output) > 0:
                logger.info(f"Model access successful. Output URL: {test_output[0]}")
                return GenerateResponse(
                    status="success",
                    message="Replicate API connection and model access successful",
                    details={
                        "client_version": version,
                        "model_id": service.replicate_model_id,
                        "test_output_url": test_output[0]
                    }
                )
            else:
                logger.warning(f"Model access test returned unexpected output: {test_output}")
                return GenerateResponse(
                    status="warning",
                    message="Replicate API connection successful but model output format unexpected",
                    details={"output": test_output}
                )
                
        except Exception as e:
            logger.error(f"Error testing model access: {str(e)}")
            return GenerateResponse(
                status="error",
                message="Replicate API connection failed",
                details={"error": str(e)}
            )
                
    except Exception as e:
        logger.error(f"Error testing Replicate API connection: {str(e)}")
        return GenerateResponse(
            status="error",
            message=f"Failed to test Replicate API connection: {str(e)}",
            details={"error_type": type(e).__name__, "error_traceback": str(e)}
        )
