import os
import logging
import traceback
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import time
import uuid
import json
import shutil
import datetime
from celery import Task

from app.celeryworker.worker import celery_app
from app.db.session import SessionLocal
from app.services.gdrive import GoogleDriveService
from app.db.models.generated_music import GeneratedMusic
from app.db.models.stem import Stem
from app.db.models.mixed_track import MixedTrack

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


# Task: Generate Music with Stems
@celery_app.task(bind=True, base=BaseTask, name="app.celeryworker.tasks.generate_music_with_stems", priority=10)
def generate_music_with_stems(self, generated_music_id: int, prompt: str, duration: int, 
                             melody_id: Optional[str] = None, proj_id: int = None, 
                             user_id: int = None) -> Dict:
    """
    Generate music with separated stems using MusicGen via Replicate API.
    
    Args:
        generated_music_id: ID of the GeneratedMusic record
        prompt: Text description of the music to generate
        duration: Duration in seconds (5-60)
        melody_id: Optional Google Drive ID of a melody audio file
        proj_id: Project ID
        user_id: User ID
        
    Returns:
        Dictionary with paths to generated stems and their Google Drive IDs
    """
    logger.info(f"Starting music generation with stems for prompt: '{prompt}'")
    
    # Get database session
    db = self.db
    
    try:
        # Update status to processing
        generated_music = db.query(GeneratedMusic).filter(GeneratedMusic.id == generated_music_id).first()
        if not generated_music:
            raise ValueError(f"GeneratedMusic record not found: {generated_music_id}")
        
        generated_music.status = "processing"
        generated_music.progress = 10
        db.commit()
        
        # Create temporary directory for processing
        temp_dir = os.path.join(TEMP_STEMS_DIR, f"generation_{generated_music_id}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download melody file if provided
        melody_path = None
        if melody_id:
            logger.info(f"Downloading melody file: {melody_id}")
            melody_file_path = os.path.join(temp_dir, "melody.wav")
            
            # Initialize Google Drive service
            gdrive_service = GoogleDriveService()
            
            # Download melody file
            melody_success, melody_message = gdrive_service.download_file(melody_id, melody_file_path)
            if not melody_success:
                logger.warning(f"Failed to download melody file: {melody_message}")
            else:
                melody_path = melody_file_path
                logger.info(f"Melody file downloaded to {melody_path}")
        
        # Update status
        generated_music.progress = 20
        db.commit()
        
        # Generate music with stems
        from app.services.music_generation import generate_music_with_stems as generate_stems
        
        # Generate unique job ID
        job_id = f"gen_{generated_music_id}"
        
        # Call music generation service
        stem_paths = generate_stems(
            text_prompt=prompt,
            duration=duration,
            melody_path=melody_path,
            output_dir=temp_dir,
            job_id=job_id
        )
        
        # Update status
        generated_music.progress = 70
        db.commit()
        
        # Upload stems to Google Drive
        gdrive_service = GoogleDriveService()
        stem_ids = {}
        
        for stem_type, stem_path in stem_paths.items():
            # Create stem record
            stem = Stem(
                generated_music_id=generated_music_id,
                stem_type=stem_type,
                filename=os.path.basename(stem_path),
                file_size=os.path.getsize(stem_path),
                mime_type="audio/wav",
                status="uploading"
            )
            db.add(stem)
            db.commit()
            
            # Upload to Google Drive
            folder_id = gdrive_service.get_or_create_folder("music_generation")
            upload_success, file_id = gdrive_service.upload_file(
                stem_path, 
                os.path.basename(stem_path),
                folder_id,
                mime_type="audio/wav"
            )
            
            if upload_success:
                # Update stem record
                stem.gdrive_file_id = file_id
                stem.status = "completed"
                stem_ids[stem_type] = file_id
            else:
                # Mark as failed
                stem.status = "failed"
                stem.error_message = f"Failed to upload stem to Google Drive"
            
            db.commit()
        
        # Update generated music record
        generated_music.status = "completed"
        generated_music.progress = 100
        generated_music.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        
        logger.info(f"Music generation completed successfully: {generated_music_id}")
        
        # Return result
        return {
            "status": "success",
            "generated_music_id": generated_music_id,
            "stem_ids": stem_ids
        }
        
    except Exception as e:
        # Log error
        error_message = f"Error generating music with stems: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        
        # Update status
        try:
            generated_music = db.query(GeneratedMusic).filter(GeneratedMusic.id == generated_music_id).first()
            if generated_music:
                generated_music.status = "failed"
                generated_music.error_message = error_message
                db.commit()
        except Exception as db_error:
            logger.error(f"Error updating GeneratedMusic status: {str(db_error)}")
        
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        
        # Re-raise exception
        raise

# Task: Mix Stems
@celery_app.task(bind=True, base=BaseTask, name="app.celeryworker.tasks.mix_stems", priority=5)
def mix_stems(self, mixed_track_id: int, selected_stems: List[str], volume_levels: Optional[Dict[str, float]] = None) -> Dict:
    """
    Mix selected stems with optional volume adjustments.
    
    Args:
        mixed_track_id: ID of the MixedTrack record
        selected_stems: List of stem types to include in the mix
        volume_levels: Optional dictionary mapping stem types to volume factors
        
    Returns:
        Dictionary with path to mixed track and its Google Drive ID
    """
    logger.info(f"Starting stem mixing for track: {mixed_track_id}")
    
    # Get database session
    db = self.db
    
    try:
        # Get mixed track record
        mixed_track = db.query(MixedTrack).filter(MixedTrack.id == mixed_track_id).first()
        if not mixed_track:
            raise ValueError(f"MixedTrack record not found: {mixed_track_id}")
        
        # Update status
        mixed_track.status = "processing"
        db.commit()
        
        # Get generated music record
        generated_music = db.query(GeneratedMusic).filter(GeneratedMusic.id == mixed_track.generated_music_id).first()
        if not generated_music:
            raise ValueError(f"GeneratedMusic record not found: {mixed_track.generated_music_id}")
        
        # Get stems
        stems = db.query(Stem).filter(
            Stem.generated_music_id == generated_music.id,
            Stem.stem_type.in_(selected_stems)
        ).all()
        
        if not stems:
            raise ValueError(f"No stems found for selected types: {selected_stems}")
        
        # Create temporary directory for processing
        temp_dir = os.path.join(TEMP_STEMS_DIR, f"mix_{mixed_track_id}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download stems
        gdrive_service = GoogleDriveService()
        stem_paths = {}
        
        for stem in stems:
            if not stem.gdrive_file_id:
                logger.warning(f"Stem {stem.id} ({stem.stem_type}) has no Google Drive ID, skipping")
                continue
            
            # Download stem
            stem_path = os.path.join(temp_dir, f"{stem.stem_type}.wav")
            download_success, message = gdrive_service.download_file(stem.gdrive_file_id, stem_path)
            
            if not download_success:
                logger.warning(f"Failed to download stem {stem.id}: {message}")
                continue
            
            stem_paths[stem.stem_type] = stem_path
        
        if not stem_paths:
            raise ValueError("Failed to download any stems")
        
        # Update status
        mixed_track.progress = 50
        db.commit()
        
        # Mix stems
        from app.services.audio_mixing import mix_audio_stems
        
        output_path = os.path.join(temp_dir, f"mixed_{mixed_track_id}.wav")
        mixed_path = mix_audio_stems(
            stem_paths=stem_paths,
            volume_levels=volume_levels,
            output_path=output_path
        )
        
        # Update status
        mixed_track.progress = 80
        db.commit()
        
        # Upload mixed track to Google Drive
        folder_id = gdrive_service.get_or_create_folder("mixed_tracks")
        upload_success, file_id = gdrive_service.upload_file(
            mixed_path,
            os.path.basename(mixed_path),
            folder_id,
            mime_type="audio/wav"
        )
        
        if not upload_success:
            raise ValueError("Failed to upload mixed track to Google Drive")
        
        # Update mixed track record
        mixed_track.gdrive_file_id = file_id
        mixed_track.file_size = os.path.getsize(mixed_path)
        mixed_track.status = "completed"
        mixed_track.progress = 100
        mixed_track.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        
        logger.info(f"Stem mixing completed successfully: {mixed_track_id}")
        
        # Return result
        return {
            "status": "success",
            "mixed_track_id": mixed_track_id,
            "gdrive_file_id": file_id
        }
        
    except Exception as e:
        # Log error
        error_message = f"Error mixing stems: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        
        # Update status
        try:
            mixed_track = db.query(MixedTrack).filter(MixedTrack.id == mixed_track_id).first()
            if mixed_track:
                mixed_track.status = "failed"
                mixed_track.error_message = error_message
                db.commit()
        except Exception as db_error:
            logger.error(f"Error updating MixedTrack status: {str(db_error)}")
        
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        
        # Re-raise exception
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