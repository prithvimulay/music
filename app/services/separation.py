# app/services/separation.py
import os
import subprocess
import logging
import uuid

logger = logging.getLogger(__name__)

def separate_stems(audio_path: str, output_dir: str) -> dict:
    """
    Separate an audio file into stems using Demucs.
    
    Args:
        audio_path: Path to the audio file
        output_dir: Directory to store the stems
        
    Returns:
        Dictionary with paths to the separated stems
    """
    logger.info(f"Separating stems for {audio_path}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a unique ID for this separation
    separation_id = uuid.uuid4().hex
    
    try:
        # Run Demucs command
        cmd = [
            "demucs", 
            "--out", output_dir,
            "--two-stems=vocals",  # Separate into vocals and accompaniment
            audio_path
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Get paths to the separated stems
        track_name = os.path.splitext(os.path.basename(audio_path))[0]
        stems_dir = os.path.join(output_dir, "htdemucs", track_name)
        
        # Check if the stems were created
        vocals_path = os.path.join(stems_dir, "vocals.wav")
        accompaniment_path = os.path.join(stems_dir, "no_vocals.wav")
        
        if not os.path.exists(vocals_path) or not os.path.exists(accompaniment_path):
            raise FileNotFoundError(f"Stems not found in {stems_dir}")
        
        logger.info(f"Stems separated successfully: {stems_dir}")
        
        # Return paths to the stems
        return {
            "vocals": vocals_path,
            "accompaniment": accompaniment_path
        }
    except Exception as e:
        logger.error(f"Error separating stems: {str(e)}")
        raise