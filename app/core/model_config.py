"""
Configuration utilities for AI models.
"""
import os
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

def get_model_config() -> Dict[str, Any]:
    """
    Get configuration for AI models based on environment variables.
    
    Returns:
        Dictionary with model configuration settings
    """
    # Get Hugging Face token
    hf_token = os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        logger.warning("HUGGINGFACE_TOKEN not set. Some models may not be accessible.")
    
    # MusicGen configuration
    musicgen_config = {
        "use_huggingface": os.environ.get("USE_HUGGINGFACE_MODEL", "true").lower() == "true",
        "model_id": os.environ.get("MUSICGEN_MODEL_ID", "facebook/musicgen-small"),
        "device": os.environ.get("MUSICGEN_DEVICE", None),  # None will auto-detect
        "cache_dir": os.environ.get("AUDIOCRAFT_CACHE_DIR", "/app/.cache"),
        "token": hf_token,
    }
    
    # Log the configuration (but mask the token)
    safe_config = musicgen_config.copy()
    if hf_token:
        safe_config["token"] = "****" + hf_token[-4:] if len(hf_token) > 4 else "****"
    logger.info(f"MusicGen configuration: {safe_config}")
    
    return {
        "musicgen": musicgen_config,
    }

def get_musicgen_config() -> Dict[str, Any]:
    """
    Get MusicGen-specific configuration.
    
    Returns:
        Dictionary with MusicGen configuration
    """
    return get_model_config()["musicgen"]

def verify_huggingface_token() -> bool:
    """
    Verify that the Hugging Face token is set and valid.
    
    Returns:
        True if token is set, False otherwise
    """
    token = os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        logger.warning("HUGGINGFACE_TOKEN environment variable is not set")
        return False
    
    # Simple validation - just check if it starts with 'hf_'
    if not token.startswith("hf_"):
        logger.warning("HUGGINGFACE_TOKEN does not appear to be valid (should start with 'hf_')")
        return False
        
    return True
