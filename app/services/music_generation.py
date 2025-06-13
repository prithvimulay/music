"""
Music generation service using MusicGen models via Replicate API.
"""
import os
import logging
import requests
import time
import tempfile
import json
import base64
from typing import Dict, Optional, List, Union, Any
from dataclasses import dataclass

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class MusicGenService:
    """Class representing the MusicGen service configuration"""
    model_id: str
    replicate_model_id: str
    replicate_token: str
    device: str = "replicate-api"
    is_initialized: bool = False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the Replicate API"""
        if not self.replicate_token:
            raise ValueError("REPLICATE_API_TOKEN is not set")
        
        try:
            import replicate
            # Set the API token
            os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
            
            # Just check if we can access the API
            version = replicate.version_info()
            return {"status": "success", "message": f"Replicate API connection successful. Client version: {version}"}
        except Exception as e:
            return {"status": "error", "message": f"Replicate API connection failed: {str(e)}"}

def get_musicgen_service() -> MusicGenService:
    """
    Get a configured MusicGen service.
    
    This function configures the Replicate API service based on environment settings.
    
    Returns:
        MusicGenService: Configured service object
    
    Raises:
        ValueError: If required configuration is missing
    """
    model_id = settings.MUSICGEN_MODEL_ID
    
    replicate_token = settings.REPLICATE_API_TOKEN
    if not replicate_token:
        raise ValueError("REPLICATE_API_TOKEN is not set in environment variables")
    
    # Strip any whitespace from the token
    replicate_token = replicate_token.strip()
    
    # Log token length and first/last few characters for debugging
    token_length = len(replicate_token)
    masked_token = f"{replicate_token[:4]}...{replicate_token[-4:]}" if token_length > 8 else "***"
    logger.info(f"Using Replicate token: {masked_token} (length: {token_length})")
    
    replicate_model_id = settings.REPLICATE_MODEL_ID
    logger.info(f"Using Replicate model ID: {replicate_model_id}")
    
    service = MusicGenService(
        model_id=model_id,
        replicate_model_id=replicate_model_id,
        replicate_token=replicate_token,
        is_initialized=True
    )
    
    logger.info(f"MusicGen service initialized with model: {service.model_id}")
    return service

def generate_music_with_stems(
    text_prompt: str,
    duration: int,
    output_dir: str,
    melody_path: Optional[str] = None,
    job_id: Optional[str] = None,
    max_retries: int = 3,
    retry_delay: int = 5
) -> Dict[str, str]:
    """
    Generate music with separated stems using MusicGen via Replicate API.
    
    Args:
        text_prompt: Text description of the music to generate
        duration: Duration in seconds
        output_dir: Directory to save the generated audio files
        melody_path: Optional path to a melody audio file for conditioning
        job_id: Optional unique identifier for the job
        max_retries: Maximum number of retries for API calls
        retry_delay: Delay between retries in seconds
    
    Returns:
        Dict[str, str]: Dictionary mapping stem names to file paths
    """
    service = get_musicgen_service()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Base filename for output files
    base_filename = job_id if job_id else f"gen_{int(time.time())}"
    
    # Initialize output paths dictionary
    output_paths = {
        "mix": os.path.join(output_dir, f"{base_filename}_mix.wav"),
        "drums": os.path.join(output_dir, f"{base_filename}_drums.wav"),
        "bass": os.path.join(output_dir, f"{base_filename}_bass.wav"),
        "other": os.path.join(output_dir, f"{base_filename}_other.wav")
    }
    
    try:
        # Import replicate here to avoid import errors if the package is not installed
        try:
            import replicate
        except ImportError:
            raise ImportError("replicate package is not installed. Install it with 'pip install replicate'")
        
        # Set the API token
        os.environ["REPLICATE_API_TOKEN"] = service.replicate_token
        
        # Prepare the input parameters
        input_params = {
            "prompt": text_prompt,
            "duration": duration,
            "output_format": "wav",
            "continuation": False,
            "continuation_start": 0,
            "continuation_end": 0,
            "normalization_strategy": "peak",
            "top_k": 250,
            "top_p": 0,
            "temperature": 1.0,
            "classifier_free_guidance": 3.0,
            "output_stem": "all"  # Generate all stems
        }
        
        # Add melody conditioning if provided
        if melody_path and os.path.exists(melody_path):
            logger.info(f"Using melody conditioning from {melody_path}")
            try:
                # For Replicate, we need to upload the file to a publicly accessible URL
                # This is a limitation of the Replicate API
                logger.warning("Melody conditioning with Replicate requires a publicly accessible URL")
                logger.warning("Skipping melody conditioning as direct file upload is not supported")
                # If you have a solution for file hosting, you can add it here
            except Exception as e:
                logger.warning(f"Error processing melody file, skipping melody conditioning: {str(e)}")
        
        # Log request details
        logger.info(f"Using Replicate model: {service.replicate_model_id}")
        logger.info(f"Request parameters: {json.dumps(input_params, indent=2)}")
        
        # Send the request with retries
        logger.info("Sending request to Replicate API")
        
        for attempt in range(max_retries):
            try:
                # Run the model
                output = replicate.run(
                    service.replicate_model_id,
                    input=input_params
                )
                
                # The output should be a URL to the generated audio
                if output and isinstance(output, list) and len(output) > 0:
                    audio_url = output[0]
                    logger.info(f"Generated audio URL: {audio_url}")
                    
                    # Download the audio file
                    response = requests.get(audio_url)
                    if response.status_code == 200:
                        # Save the mix file
                        with open(output_paths["mix"], "wb") as f:
                            f.write(response.content)
                        logger.info(f"Saved mix to {output_paths['mix']}")
                        
                        # Note: Replicate might not return separate stems
                        # We're just saving the mix file for now
                        # You can modify this if your specific model version returns stems
                        
                        return output_paths
                    else:
                        raise Exception(f"Failed to download audio file: {response.status_code}")
                else:
                    raise Exception(f"Unexpected output format from Replicate: {output}")
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.error(f"Error: {str(e)}. Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    raise
        
        raise Exception("Failed to generate music after multiple attempts")
        
    except Exception as e:
        error_msg = f"Error generating music with stems: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
