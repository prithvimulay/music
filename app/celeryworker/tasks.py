import os
import logging
import traceback
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import time
import uuid
import json
import shutil
from celery import Task

from app.celeryworker.worker import celery_app
from app.db.session import SessionLocal
from app.services.gdrive import gdrive_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADED_TRACKS_DIR = os.path.join(BASE_DIR, "uploaded_tracks")
GENERATED_TRACKS_DIR = os.path.join(BASE_DIR, "generated_tracks")
TEMP_STEMS_DIR = os.path.join(BASE_DIR, "temp_stems")

# Ensure directories exist
os.makedirs(UPLOADED_TRACKS_DIR, exist_ok=True)
os.makedirs(GENERATED_TRACKS_DIR, exist_ok=True)
os.makedirs(TEMP_STEMS_DIR, exist_ok=True)

# Create a base task class for common functionality
class BaseTask(Task):
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


# Task 1: Stem Separation
@celery_app.task(bind=True, base=BaseTask, name="app.celeryworker.tasks.stem_separation", priority=10)
def stem_separation(self, track1_id: str, track2_id: str, project_id: int, user_id: int) -> Dict:
    """
    Separate audio tracks into stems using Demucs.
    
    Args:
        track1_id: Google Drive ID of the first track
        track2_id: Google Drive ID of the second track
        project_id: Project ID
        user_id: User ID
        
    Returns:
        Dictionary with paths to separated stems
    """
    logger.info(f"Starting stem separation for tracks {track1_id} and {track2_id}")
    
    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 4,
                "status": "Downloading tracks"
            }
        )
        
        # Download files from Google Drive
        logger.info(f"Downloading track1 with ID: {track1_id}")
        track1_file_path = os.path.join(UPLOADED_TRACKS_DIR, f"track1_{track1_id}.wav")
        track1_success, track1_message = gdrive_service.download_file(track1_id, track1_file_path)
        if not track1_success:
            raise Exception(f"Failed to download track1: {track1_message}")
        track1_path = track1_file_path
        
        logger.info(f"Downloading track2 with ID: {track2_id}")
        track2_file_path = os.path.join(UPLOADED_TRACKS_DIR, f"track2_{track2_id}.wav")
        track2_success, track2_message = gdrive_service.download_file(track2_id, track2_file_path)
        if not track2_success:
            raise Exception(f"Failed to download track2: {track2_message}")
        track2_path = track2_file_path
        
        # Get metadata for the tracks
        logger.info(f"Getting metadata for track1 with ID: {track1_id}")
        track1_metadata = gdrive_service.get_file_metadata(track1_id)
        logger.info(f"Getting metadata for track2 with ID: {track2_id}")
        track2_metadata = gdrive_service.get_file_metadata(track2_id)
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 4,
                "status": "Creating stem directory"
            }
        )
        
        # Create stem directory
        stem_dir = os.path.join(TEMP_STEMS_DIR, f"fusion_{uuid.uuid4().hex}")
        os.makedirs(stem_dir, exist_ok=True)
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 4,
                "status": "Separating stems for track 1"
            }
        )
        
        # Use Demucs for stem separation
        import numpy as np
        import librosa
        from app.services.separation import separate_stems
        
        stems = {}
        stems["track1"] = separate_stems(track1_path, os.path.join(stem_dir, "track1"))
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 4,
                "total": 4,
                "status": "Separating stems for track 2"
            }
        )
        
        stems["track2"] = separate_stems(track2_path, os.path.join(stem_dir, "track2"))
        
        logger.info(f"Stem separation completed for tracks {track1_id} and {track2_id}")
        
        return {
            "stem_dir": stem_dir,
            "stems": stems,
            "project_id": project_id,
            "user_id": user_id,
            "track1_metadata": track1_metadata,
            "track2_metadata": track2_metadata,
            "track1_id": track1_id,
            "track2_id": track2_id
        }
    except Exception as e:
        logger.error(f"Error in stem separation: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise

# Task 2: Feature Extraction
@celery_app.task(bind=True, base=BaseTask, name="app.celeryworker.tasks.feature_extraction", priority=8)
def feature_extraction(self, stem_data: Dict) -> Dict:
    """
    Extract musical features from the stems.
    
    Args:
        stem_data: Dictionary with paths to separated stems
        
    Returns:
        Dictionary with extracted features
    """
    logger.info("Starting feature extraction")
    
    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 4,
                "status": "Extracting features from track 1 vocals"
            }
        )
        
        import numpy as np
        from app.services.mir import extract_features
        
        # Extract features from each stem
        features = {
            "track1": {},
            "track2": {}
        }
        
        # Process track 1
        track1_vocals = stem_data["stems"]["track1"]["vocals"]
        features["track1"]["vocals"] = extract_features(track1_vocals)
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 4,
                "status": "Extracting features from track 1 accompaniment"
            }
        )
        
        track1_accompaniment = stem_data["stems"]["track1"]["accompaniment"]
        features["track1"]["accompaniment"] = extract_features(track1_accompaniment)
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 4,
                "status": "Extracting features from track 2 vocals"
            }
        )
        
        # Process track 2
        track2_vocals = stem_data["stems"]["track2"]["vocals"]
        features["track2"]["vocals"] = extract_features(track2_vocals)
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 4,
                "total": 4,
                "status": "Extracting features from track 2 accompaniment"
            }
        )
        
        track2_accompaniment = stem_data["stems"]["track2"]["accompaniment"]
        features["track2"]["accompaniment"] = extract_features(track2_accompaniment)
        
        # Aggregate features for each track
        for track in ["track1", "track2"]:
            features[track]["tempo"] = (features[track]["vocals"]["tempo"] + features[track]["accompaniment"]["tempo"]) / 2
            features[track]["energy"] = (features[track]["vocals"]["energy"] + features[track]["accompaniment"]["energy"]) / 2
            features[track]["danceability"] = (features[track]["vocals"]["danceability"] + features[track]["accompaniment"]["danceability"]) / 2
        
        logger.info("Feature extraction completed")
        
        return {
            **stem_data,
            "features": features
        }
    except Exception as e:
        logger.error(f"Error in feature extraction: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise

# Task 3: Generate Fusion
@celery_app.task(bind=True, base=BaseTask, name="app.celeryworker.tasks.generate_fusion", priority=6)
def generate_fusion(self, feature_data: Dict, duration: int = 15, temperature: float = 1.0, 
                   prompt_guidance: float = 3.0, custom_prompt: str = None) -> Dict:
    """
    Generate a fusion track using the extracted features.
    
    Args:
        feature_data: Dictionary with extracted features
        duration: Duration in seconds (5-30)
        temperature: Controls randomness (0.1-1.5)
        prompt_guidance: Controls adherence to prompt (1.0-7.0)
        custom_prompt: User-provided prompt
        
    Returns:
        Dictionary with path to generated fusion track
    """
    logger.info("Starting fusion generation")
    
    try:
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 3,
                "status": "Loading MusicGen model"
            }
        )
        
        # Import here to avoid loading the model at module import time
        from app.services.music_generation import get_musicgen_service
        
        # Get the MusicGen service (loads model on first call)
        musicgen = get_musicgen_service()
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 3,
                "status": "Creating prompt and generating audio"
            }
        )
        
        # Create a prompt based on extracted features
        track1_features = feature_data["features"]["track1"]
        track2_features = feature_data["features"]["track2"]
        
        # Calculate target tempo (average of the two tracks)
        target_tempo = (track1_features["tempo"] + track2_features["tempo"]) / 2
        
        # Create a descriptive prompt for MusicGen
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = f"Create a fusion track with tempo {target_tempo:.1f} BPM, "
            prompt += f"combining the energy of track 1 ({track1_features['energy']:.2f}) and "
            prompt += f"the danceability of track 2 ({track2_features['danceability']:.2f}). "
        
        logger.info(f"Generated prompt: {prompt}")
        
        # Ensure parameters are within valid ranges
        safe_duration = max(5, min(30, duration))
        safe_guidance_scale = max(1.0, min(7.0, prompt_guidance))
        
        # Generate audio with user parameters
        fusion_filename = f"fusion_{uuid.uuid4().hex}.wav"
        fusion_track_path = os.path.join(GENERATED_TRACKS_DIR, fusion_filename)
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 3,
                "status": "Generating audio with MusicGen"
            }
        )
        
        # Generate the audio using our service
        musicgen.generate(
            prompt=prompt,
            duration=safe_duration,
            guidance_scale=safe_guidance_scale,
            output_path=fusion_track_path,
            num_inference_steps=50
        )
        
        logger.info(f"Fusion track generated and saved to {fusion_track_path}")
        
        return {
            **feature_data,
            "fusion_track_path": fusion_track_path,
            "fusion_filename": fusion_filename,
            "prompt": prompt,
            "generation_params": {
                "duration": safe_duration,
                "guidance_scale": safe_guidance_scale
            },
            "start_time": time.time()  # For tracking processing time
        }
    except Exception as e:
        logger.error(f"Error in fusion generation: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise

# Task 4: Audio Enhancement
@celery_app.task(bind=True, base=BaseTask, name="app.celeryworker.tasks.enhance_audio", priority=4)
def enhance_audio(self, fusion_data: Dict) -> Dict:
    """
    Enhance the generated fusion track with real audio processing techniques.
    
    Args:
        fusion_data: Dictionary with path to generated fusion track
        
    Returns:
        Dictionary with path to enhanced fusion track and Google Drive ID
    """
    logger.info("Starting real audio enhancement")
    
    try:
        stem_dir = fusion_data["stem_dir"]
        fusion_track_path = fusion_data["fusion_track_path"]
        fusion_filename = fusion_data["fusion_filename"]
        project_id = fusion_data["project_id"]
        user_id = fusion_data["user_id"]
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 5,
                "status": "Loading audio for enhancement"
            }
        )
        
        # 1. Apply audio enhancement techniques to the fusion track
        try:
            # Load the audio file
            logger.info(f"Loading audio file: {fusion_track_path}")
            import librosa
            y, sr = librosa.load(fusion_track_path, sr=None)
            logger.info(f"Audio loaded successfully: {len(y)/sr:.2f} seconds, {sr} Hz")
            
            # Update task state
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 2,
                    "total": 5,
                    "status": "Applying audio enhancements"
                }
            )
            
            # Apply a series of enhancements
            logger.info("Applying audio enhancements")
            
            # 1.1 Normalize audio to prevent clipping
            logger.info("Normalizing audio")
            import numpy as np
            y_norm = np.array(y) / np.max(np.abs(y))
            
            # 1.2 Apply compression (reduce dynamic range)
            logger.info("Applying compression")
            # Simple compression algorithm
            threshold = 0.5
            ratio = 4.0
            y_compressed = np.copy(y_norm)
            mask = np.abs(y_compressed) > threshold
            y_compressed[mask] = threshold + (np.abs(y_compressed[mask]) - threshold) / ratio * np.sign(y_compressed[mask])
            
            # 1.3 Apply EQ (boost bass slightly)
            logger.info("Applying EQ")
            try:
                # Apply a low-shelf filter to boost bass frequencies
                from scipy import signal
                b, a = signal.butter(2, 200/(sr/2), btype='lowshelf', analog=False)
                y_eq = signal.lfilter(b, a, y_compressed)
            except ImportError:
                logger.warning("scipy not available, skipping EQ")
                y_eq = y_compressed
            
            # 1.4 Final limiter to prevent clipping
            logger.info("Applying final limiter")
            y_final = np.clip(y_eq, -0.98, 0.98)
            
            # Update task state
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 3,
                    "total": 5,
                    "status": "Saving enhanced audio"
                }
            )
            
            # 2. Save the enhanced track to a file
            enhanced_filename = fusion_filename.replace(".wav", "_enhanced.wav")
            if not enhanced_filename.endswith(".wav"):
                enhanced_filename += ".wav"
                
            enhanced_track_path = os.path.join(GENERATED_TRACKS_DIR, enhanced_filename)
            logger.info(f"Saving enhanced track to: {enhanced_track_path}")
            
            # Save the audio file
            import soundfile as sf
            sf.write(enhanced_track_path, y_final, sr)
            logger.info("Enhanced track saved successfully")
            
            # Update task state
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 4,
                    "total": 5,
                    "status": "Uploading to Google Drive"
                }
            )
            
            # 3. Upload the enhanced track to Google Drive
            logger.info("Uploading enhanced track to Google Drive")
            gdrive_file_id = gdrive_service.upload_file(
                file_path=enhanced_track_path,
                name=enhanced_filename
            )
            logger.info(f"Uploaded to Google Drive with ID: {gdrive_file_id}")
            
            # Update task state
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 5,
                    "total": 5,
                    "status": "Saving to database"
                }
            )
            
            # 4. Save the metadata to the database
            logger.info("Saving metadata to database")
            
            # Create fusion metadata
            fusion_metadata = {
                "features": fusion_data.get("features", {}),
                "enhancement": {
                    "normalization": True,
                    "compression": {"threshold": threshold, "ratio": ratio},
                    "eq": "bass_boost",
                    "limiter": True
                },
                "processing_time": time.time() - fusion_data.get("start_time", time.time())
            }
            
            # Create a new audio file record in the database
            from app.db.models.audio_file import AudioFile as AudioFileModel
            new_audio_file = AudioFileModel(
                filename=enhanced_filename,
                gdrive_file_id=gdrive_file_id,
                proj_id=project_id,
                user_id=user_id,
                is_fusion=True,
                source_track1_id=fusion_data["track1_metadata"]["id"],
                source_track2_id=fusion_data["track2_metadata"]["id"],
                fusion_metadata=json.dumps(fusion_metadata)
            )
            
            self.db.add(new_audio_file)
            self.db.commit()
            self.db.refresh(new_audio_file)
            logger.info(f"Created database record with ID: {new_audio_file.id}")
            
            # Clean up stem directory
            import shutil
            shutil.rmtree(stem_dir, ignore_errors=True)
            
            # 5. Return the Google Drive ID and metadata
            logger.info("Audio enhancement completed successfully")
            return {
                "file_id": new_audio_file.id,
                "gdrive_file_id": gdrive_file_id,
                "filename": enhanced_filename,
                "project_id": project_id,
                "user_id": user_id,
                "fusion_metadata": fusion_metadata
            }
            
        except Exception as e:
            logger.error(f"Error in audio processing: {str(e)}")
            raise
    
    except Exception as e:
        logger.error(f"Error in audio enhancement: {str(e)}")
        # Clean up stem directory if it exists
        if 'stem_dir' in locals():
            import shutil
            shutil.rmtree(stem_dir, ignore_errors=True)
        raise

# Utility task for cleaning up temporary files
@celery_app.task(name="app.celeryworker.tasks.cleanup_temp_files")
def cleanup_temp_files():
    """Cleanup temporary files that are older than 24 hours"""
    current_time = time.time()
    
    # Clean up old files in the temp_stems directory
    for item in os.listdir(TEMP_STEMS_DIR):
        item_path = os.path.join(TEMP_STEMS_DIR, item)
        if os.path.isdir(item_path):
            try:
                dir_stat = os.stat(item_path)
                # If directory is older than 24 hours
                if current_time - dir_stat.st_mtime > 86400:
                    import shutil
                    shutil.rmtree(item_path, ignore_errors=True)
                    logger.info(f"Cleaned up temporary directory: {item_path}")
            except Exception as e:
                logger.error(f"Error cleaning up directory {item_path}: {str(e)}")
    
    return {"status": "success", "message": "Temporary files cleanup completed"}