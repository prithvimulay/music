# app/services/mir.py
import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)

def extract_features(audio_path: str) -> dict:
    """
    Extract musical features from an audio file.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Dictionary with extracted features
    """
    logger.info(f"Extracting features from {audio_path}")
    
    try:
        # Load the audio file
        y, sr = librosa.load(audio_path, sr=None)
        
        # Extract tempo
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        
        # Extract key
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key = librosa.feature.tonnetz(chroma=chroma)
        
        # Extract energy
        rms = librosa.feature.rms(y=y)[0]
        energy = np.mean(rms)
        
        # Extract danceability (approximation based on beat strength)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        danceability = np.mean(onset_env)
        
        # Extract spectral features
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0])
        spectral_bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0])
        
        logger.info(f"Features extracted successfully from {audio_path}")
        
        return {
            "tempo": float(tempo),
            "key": key.mean(axis=1).tolist(),
            "energy": float(energy),
            "danceability": float(danceability),
            "spectral_centroid": float(spectral_centroid),
            "spectral_bandwidth": float(spectral_bandwidth)
        }
    except Exception as e:
        logger.error(f"Error extracting features: {str(e)}")
        raise