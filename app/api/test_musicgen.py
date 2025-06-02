"""
Test endpoint for MusicGen model access.
"""
import logging
import os
from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.music_generation import get_musicgen_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


class MusicGenTestResponse(BaseModel):
    status: str
    message: str
    model_id: str
    device: str
    token_available: bool
    details: Dict = None


@router.get("/test-musicgen/", response_model=MusicGenTestResponse)
async def test_musicgen_access():
    """
    Test if the MusicGen model can be accessed properly.
    """
    try:
        # Check if HUGGINGFACE_TOKEN is set
        token_available = bool(os.environ.get("HUGGINGFACE_TOKEN"))
        
        logger.info(f"Testing MusicGen model access. Token available: {token_available}")
        
        # Try to initialize the MusicGen service
        musicgen = get_musicgen_service()
        
        return MusicGenTestResponse(
            status="success",
            message="MusicGen model initialized successfully",
            model_id=musicgen.model_id,
            device=musicgen.device,
            token_available=token_available
        )
    except Exception as e:
        logger.error(f"Error initializing MusicGen model: {str(e)}")
        return MusicGenTestResponse(
            status="error",
            message=f"Failed to initialize MusicGen model: {str(e)}",
            model_id="unknown",
            device="unknown",
            token_available=token_available,
            details={"error_type": type(e).__name__, "error_traceback": str(e)}
        )
