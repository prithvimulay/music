"""
Music generation service using Hugging Face's implementation of MusicGen.
"""
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import torch
import numpy as np
import soundfile as sf
from transformers import AutoProcessor, MusicgenForConditionalGeneration

from app.core.model_config import get_musicgen_config

# Configure logging
logger = logging.getLogger(__name__)

class MusicGenService:
    """Service for generating music using Facebook's MusicGen model via Hugging Face."""
    
    def __init__(
        self,
        model_id: Optional[str] = None,
        device: Optional[str] = None,
        use_cache: bool = True,
        cache_dir: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """
        Initialize the MusicGen service.
        
        Args:
            model_id: Hugging Face model ID for MusicGen
            device: Device to use for inference ('cuda', 'cpu', or None for auto-detection)
            use_cache: Whether to use the Hugging Face cache
            cache_dir: Directory to use for caching models
            token: Hugging Face API token for accessing gated models
        """
        # Get configuration from environment
        config = get_musicgen_config()
        
        # Use provided values or fall back to config
        self.model_id = model_id or config["model_id"]
        cache_dir = cache_dir or config["cache_dir"]
        token = token or os.environ.get("HUGGINGFACE_TOKEN")
        
        # Auto-detect device if not specified
        if device is None:
            device = config["device"]
            
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        logger.info(f"Initializing MusicGen with model {self.model_id} on {self.device}")
        
        # Load model and processor
        try:
            self.processor = AutoProcessor.from_pretrained(
                self.model_id, 
                cache_dir=cache_dir if use_cache else None,
                token=token
            )
            
            self.model = MusicgenForConditionalGeneration.from_pretrained(
                self.model_id,
                cache_dir=cache_dir if use_cache else None,
                token=token
            ).to(self.device)
            
            logger.info(f"MusicGen model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading MusicGen model: {str(e)}")
            if "401" in str(e) and token is None:
                logger.error("Authentication error. Please provide a valid Hugging Face token.")
            raise
    
    def generate(
        self,
        prompt: str,
        duration: float = 8.0,
        guidance_scale: float = 3.0,
        num_inference_steps: int = 50,
        output_path: Optional[str] = None,
        seed: Optional[int] = None,
        return_audio: bool = False,
    ) -> Union[str, np.ndarray]:
        """
        Generate music based on a text prompt.
        
        Args:
            prompt: Text description of the music to generate
            duration: Duration of the generated audio in seconds
            guidance_scale: Guidance scale for classifier-free guidance
            num_inference_steps: Number of denoising steps
            output_path: Path to save the generated audio (if None, a temporary file is created)
            seed: Random seed for reproducibility
            return_audio: Whether to return the audio array instead of the file path
            
        Returns:
            Path to the generated audio file or the audio array if return_audio=True
        """
        logger.info(f"Generating music with prompt: '{prompt}'")
        
        # Set random seed if provided
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)
        
        # Prepare inputs
        inputs = self.processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        ).to(self.device)
        
        # Calculate max_new_tokens based on duration
        # MusicGen generates audio at 32000 Hz with 1 token per 50 samples
        sample_rate = 32000
        tokens_per_second = sample_rate / 50
        max_new_tokens = int(duration * tokens_per_second)
        
        # Generate audio
        with torch.no_grad():
            generated_audio = self.model.generate(
                **inputs,
                guidance_scale=guidance_scale,
                max_new_tokens=max_new_tokens,
                num_inference_steps=num_inference_steps,
                do_sample=True,
            )
        
        # Process the output
        audio_array = self.processor.batch_decode(generated_audio, return_tensors="np")[0]
        
        # Return audio array if requested
        if return_audio:
            return audio_array
        
        # Save to the specified path or create a temporary file
        if output_path is None:
            temp_dir = Path(tempfile.gettempdir()) / "puremusic_generated"
            os.makedirs(temp_dir, exist_ok=True)
            output_path = str(temp_dir / f"generated_{int(torch.rand(1)[0] * 10000)}.wav")
        
        # Save the audio file
        sf.write(output_path, audio_array, sample_rate)
        logger.info(f"Generated audio saved to {output_path}")
        
        return output_path
    
    def generate_with_fusion_context(
        self,
        prompt: str,
        reference_audio_paths: List[str],
        duration: float = 10.0,
        guidance_scale: float = 3.0,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate music with fusion context from reference audio files.
        
        Note: This is a simplified version as full audio conditioning requires
        additional processing that's more complex than basic text-to-music.
        For full audio conditioning, consider using the audiocraft library directly.
        
        Args:
            prompt: Text description of the music to generate
            reference_audio_paths: Paths to reference audio files for inspiration
            duration: Duration of the generated audio in seconds
            guidance_scale: Guidance scale for classifier-free guidance
            output_path: Path to save the generated audio
            
        Returns:
            Path to the generated audio file
        """
        # For now, we'll just use the text prompt and ignore the reference audio
        # In a full implementation, you would extract features from the reference audio
        # and use them to condition the generation
        
        enhanced_prompt = f"Create a fusion of musical styles inspired by reference tracks with: {prompt}"
        return self.generate(
            prompt=enhanced_prompt,
            duration=duration,
            guidance_scale=guidance_scale,
            output_path=output_path
        )


# Singleton instance for reuse
_musicgen_service = None

def get_musicgen_service(
    model_id: Optional[str] = None,
    force_reload: bool = False
) -> MusicGenService:
    """
    Get a singleton instance of the MusicGen service.
    
    Args:
        model_id: Hugging Face model ID to use (defaults to environment variable or 'facebook/musicgen-small')
        force_reload: Whether to force reloading the model
        
    Returns:
        MusicGen service instance
    """
    global _musicgen_service
    
    # Use model ID from environment variable if not specified
    if model_id is None:
        model_id = os.environ.get("MUSICGEN_MODEL_ID", "facebook/musicgen-small")
    
    # Initialize service if not already initialized or force_reload is True
    if _musicgen_service is None or force_reload:
        _musicgen_service = MusicGenService(model_id=model_id)
    
    return _musicgen_service
