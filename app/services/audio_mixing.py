"""
Audio mixing service for combining stems with volume adjustments.
"""
import os
import logging
import numpy as np
import soundfile as sf
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def adjust_volume(audio_data: np.ndarray, volume_factor: float) -> np.ndarray:
    """
    Adjust the volume of an audio array by a factor.
    
    Args:
        audio_data: Audio data as numpy array
        volume_factor: Volume adjustment factor (0.0 to 2.0)
        
    Returns:
        Volume-adjusted audio data
    """
    # Clip volume factor to reasonable range
    volume_factor = max(0.0, min(2.0, volume_factor))
    
    # Apply volume adjustment
    return audio_data * volume_factor

def normalize_audio(audio_data: np.ndarray, target_level: float = 0.8) -> np.ndarray:
    """
    Normalize audio to a target peak level.
    
    Args:
        audio_data: Audio data as numpy array
        target_level: Target peak level (0.0 to 1.0)
        
    Returns:
        Normalized audio data
    """
    # Find current peak
    current_peak = np.max(np.abs(audio_data))
    
    # Avoid division by zero
    if current_peak == 0:
        return audio_data
    
    # Calculate normalization factor
    norm_factor = target_level / current_peak
    
    # Apply normalization
    return audio_data * norm_factor

def mix_audio_stems(
    stem_paths: Dict[str, str],
    volume_levels: Optional[Dict[str, float]] = None,
    output_path: str = None
) -> str:
    """
    Mix multiple audio stems with optional volume adjustments.
    
    Args:
        stem_paths: Dictionary mapping stem types to file paths
        volume_levels: Dictionary mapping stem types to volume factors (0.0 to 2.0)
        output_path: Path to save the mixed audio file
        
    Returns:
        Path to the mixed audio file
    """
    logger.info(f"Mixing {len(stem_paths)} stems")
    
    # Set default volume levels if not provided
    if volume_levels is None:
        volume_levels = {stem_type: 1.0 for stem_type in stem_paths}
    
    # Create default output path if not provided
    if output_path is None:
        output_dir = os.path.dirname(next(iter(stem_paths.values())))
        output_path = os.path.join(output_dir, "mixed_output.wav")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Load and process stems
    mixed_audio = None
    sample_rate = None
    
    for stem_type, stem_path in stem_paths.items():
        # Skip if file doesn't exist
        if not os.path.exists(stem_path):
            logger.warning(f"Stem file not found: {stem_path}")
            continue
        
        try:
            # Load audio file
            audio_data, file_sample_rate = sf.read(stem_path)
            
            # Set sample rate from first file
            if sample_rate is None:
                sample_rate = file_sample_rate
            elif sample_rate != file_sample_rate:
                logger.warning(f"Sample rate mismatch: {file_sample_rate} vs {sample_rate}")
                # In a production system, you might want to resample here
            
            # Get volume factor for this stem
            volume_factor = volume_levels.get(stem_type, 1.0)
            
            # Apply volume adjustment
            adjusted_audio = adjust_volume(audio_data, volume_factor)
            
            # Add to mix
            if mixed_audio is None:
                mixed_audio = adjusted_audio
            else:
                # Handle different shapes (mono vs stereo)
                if len(adjusted_audio.shape) != len(mixed_audio.shape):
                    if len(adjusted_audio.shape) == 1:
                        # Convert mono to stereo
                        adjusted_audio = np.column_stack((adjusted_audio, adjusted_audio))
                    else:
                        # Convert mixed_audio from mono to stereo
                        mixed_audio = np.column_stack((mixed_audio, mixed_audio))
                
                # Handle different lengths
                if adjusted_audio.shape[0] != mixed_audio.shape[0]:
                    # Use the shorter length
                    min_length = min(adjusted_audio.shape[0], mixed_audio.shape[0])
                    adjusted_audio = adjusted_audio[:min_length]
                    mixed_audio = mixed_audio[:min_length]
                
                # Mix audio
                mixed_audio = mixed_audio + adjusted_audio
                
        except Exception as e:
            logger.error(f"Error processing stem {stem_type}: {str(e)}")
    
    if mixed_audio is None:
        raise ValueError("No valid stems to mix")
    
    # Normalize the mixed audio
    mixed_audio = normalize_audio(mixed_audio)
    
    # Save mixed audio
    sf.write(output_path, mixed_audio, sample_rate)
    
    logger.info(f"Mixed audio saved to {output_path}")
    return output_path

def adjust_audio_file_volume(
    input_path: str,
    output_path: str,
    volume_factor: float = 1.0
) -> str:
    """
    Adjust the volume of an audio file and save to a new file.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to save the adjusted audio file
        volume_factor: Volume adjustment factor (0.0 to 2.0)
        
    Returns:
        Path to the adjusted audio file
    """
    try:
        # Load audio file
        audio_data, sample_rate = sf.read(input_path)
        
        # Adjust volume
        adjusted_audio = adjust_volume(audio_data, volume_factor)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save adjusted audio
        sf.write(output_path, adjusted_audio, sample_rate)
        
        return output_path
    except Exception as e:
        logger.error(f"Error adjusting audio volume: {str(e)}")
        raise
