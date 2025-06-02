# app/api/endpoints/fusion.py
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path
from sqlalchemy.orm import Session
from celery import chain
from celery.result import AsyncResult

from app.db.session import get_db
from app.db.models.audio_file import AudioFile
from app.db.models.user import User
from app.db.models.fusion import Fusion, FusionStatus as FusionStatusEnum
from app.api.auth import get_current_user
from app.schemas.fusion import FusionRequest, FusionResponse, FusionStatus, FusionPrompt, FusionInDB
from app.celeryworker.tasks import stem_separation, feature_extraction, generate_fusion, enhance_audio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/prepare-prompt/", response_model=FusionPrompt)
async def prepare_fusion_prompt(
    fusion_request: FusionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    First step of fusion generation: Extract features and generate a prompt
    that the user can review and modify before starting the actual fusion.
    duration 5 to 30 seconds
    temperature 0.1 to 1.5
    prompt_guidance 1.0 to 7.0
    """
    # Verify that the tracks exist and belong to the user
    track1 = db.query(AudioFile).filter(
        AudioFile.id == fusion_request.track1_id,
        AudioFile.user_id == current_user.id
    ).first()
    
    track2 = db.query(AudioFile).filter(
        AudioFile.id == fusion_request.track2_id,
        AudioFile.user_id == current_user.id
    ).first()
    
    if not track1 or not track2:
        raise HTTPException(status_code=404, detail="One or both tracks not found")
    
    # Create a new fusion record in the database
    fusion = Fusion(
        track1_id=fusion_request.track1_id,
        track2_id=fusion_request.track2_id,
        project_id=fusion_request.proj_id,  # Note: DB model uses project_id but schema uses proj_id
        user_id=current_user.id,
        duration=fusion_request.duration,
        temperature=fusion_request.temperature,
        prompt_guidance=fusion_request.prompt_guidance or 3.0,
        custom_prompt=fusion_request.custom_prompt,
        status=FusionStatusEnum.PENDING,
        progress=0
    )
    db.add(fusion)
    db.commit()
    db.refresh(fusion)
    
    # Start only the stem separation and feature extraction tasks
    task = chain(
        stem_separation.s(track1.gdrive_file_id, track2.gdrive_file_id, 
                         fusion_request.proj_id, current_user.id),
        feature_extraction.s()
    )
    
    # Apply the task asynchronously
    result = task.apply_async()
    
    # Update the fusion record with the task ID
    fusion.task_id = result.id
    fusion.status = FusionStatusEnum.PROCESSING
    db.commit()
    
    # Return a temporary response - the client should poll the status endpoint
    # We'll generate a placeholder prompt that will be updated when the task completes
    placeholder_prompt = f"Generating fusion between tracks {track1.filename} and {track2.filename}..."
    
    # Return the initial response with task ID
    return {
        "generated_prompt": placeholder_prompt,
        "track1_id": fusion_request.track1_id,
        "track2_id": fusion_request.track2_id,
        "proj_id": fusion_request.proj_id,
        "feature_data": {"task_id": result.id}
    }

class FusionGenerateRequest(FusionRequest):
    """Extended request model for fusion generation that includes feature data"""
    feature_data_json: Optional[str] = None

@router.post("/generate/", response_model=FusionResponse)
async def generate_fusion_track(
    fusion_request: FusionGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a fusion track using feature data from prepare-prompt.
    
    This endpoint should be called after /prepare-prompt/ with the task_id received.
    Provide the feature_data_json from the prepare-prompt response to avoid redoing stem separation.
    
    Example feature_data_json: "01d7f51e-edd1-419e-9965-23244754b036" or {"task_id": "01d7f51e-edd1-419e-9965-23244754b036"}
    """
    # Verify that the tracks exist and belong to the user
    track1 = db.query(AudioFile).filter(
        AudioFile.id == fusion_request.track1_id,
        AudioFile.user_id == current_user.id
    ).first()
    
    track2 = db.query(AudioFile).filter(
        AudioFile.id == fusion_request.track2_id,
        AudioFile.user_id == current_user.id
    ).first()
    
    if not track1 or not track2:
        raise HTTPException(status_code=404, detail="One or both tracks not found")
    
    # feature_data_json is required for this endpoint
    if not fusion_request.feature_data_json:
        raise HTTPException(
            status_code=400, 
            detail="feature_data_json is required. Call /prepare-prompt/ first to get feature data."
        )
    
    try:
        # Handle different formats of feature_data_json
        # It could be a JSON string, a task_id string, or a dictionary
        logger.info(f"Received feature_data_json: {fusion_request.feature_data_json}")
        
        if isinstance(fusion_request.feature_data_json, dict):
            # Already a dictionary
            feature_data = fusion_request.feature_data_json
        else:
            try:
                # Try to parse as JSON
                feature_data = json.loads(fusion_request.feature_data_json)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, treat as a task_id string
                task_id = fusion_request.feature_data_json.strip('"')
                feature_data = {"task_id": task_id}
        
        logger.info(f"Parsed feature_data: {feature_data}")
        
        # Validate that we have a task_id
        if not feature_data.get("task_id"):
            raise ValueError("feature_data must contain a task_id")
            
        # Start the fusion generation with the existing feature data
        # No need to redo stem separation and feature extraction
        task = chain(
            generate_fusion.s(feature_data, 
                              duration=fusion_request.duration,
                              temperature=fusion_request.temperature,
                              prompt_guidance=fusion_request.prompt_guidance,
                              custom_prompt=fusion_request.custom_prompt),
            enhance_audio.s()
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing feature_data_json: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid feature data format")
    
    result = task.apply_async()
    
    # Create a pending fusion record with current timestamp
    now = datetime.now(timezone.utc)
    
    fusion_track = AudioFile(
        filename=f"fusion_pending_{result.id}.wav",
        gdrive_file_id="pending_" + result.id,  # Use a placeholder that will be updated when the task completes
        status=FusionStatusEnum.PENDING.value,  # Use the enum value to ensure case consistency
        proj_id=fusion_request.proj_id,
        user_id=current_user.id,
        is_fusion=True,
        source_track1_id=track1.id,
        source_track2_id=track2.id,
        task_id=result.id,
        created_at=now,
        updated_at=now
    )
    
    db.add(fusion_track)
    db.commit()
    db.refresh(fusion_track)
    
    logger.info(f"Created fusion track with ID {fusion_track.id} and status {fusion_track.status}")
    
    # Make sure we return all fields required by the FusionResponse schema
    return FusionResponse(
        id=fusion_track.id,
        status=FusionStatusEnum.PENDING,  # Use enum directly, not the string value
        task_id=result.id,
        progress=0,
        error_message=None
    ).model_dump()

@router.get("/status/{fusion_id}", response_model=FusionStatus)
async def get_fusion_status(
    fusion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of a fusion task."""
    fusion_track = db.query(AudioFile).filter(
        AudioFile.id == fusion_id,
        AudioFile.user_id == current_user.id,
        AudioFile.is_fusion == True
    ).first()
    
    if not fusion_track:
        raise HTTPException(status_code=404, detail="Fusion track not found")
    
    # Ensure we have updated_at field
    if not hasattr(fusion_track, 'updated_at') or fusion_track.updated_at is None:
        fusion_track.updated_at = fusion_track.created_at
        db.commit()
    
    # Convert status to proper enum if needed
    if fusion_track.status.upper() in [e.name for e in FusionStatusEnum]:
        status = FusionStatusEnum[fusion_track.status.upper()]
    else:
        # Default to pending if status is invalid
        status = FusionStatusEnum.PENDING
    
    # Create a proper FusionStatus response
    return FusionStatus(
        id=fusion_track.id,
        status=status,
        progress=fusion_track.progress or 0,
        error_message=fusion_track.error_message,
        output_filename=fusion_track.filename,
        gdrive_file_id=fusion_track.gdrive_file_id,
        created_at=fusion_track.created_at,
        updated_at=fusion_track.updated_at or fusion_track.created_at,
        completed_at=fusion_track.completed_at
    ).model_dump()

@router.get("/download/{fusion_id}")
async def download_fusion(
    fusion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a completed fusion track."""
    fusion_track = db.query(AudioFile).filter(
        AudioFile.id == fusion_id,
        AudioFile.user_id == current_user.id,
        AudioFile.is_fusion == True
    ).first()
    
    if not fusion_track:
        raise HTTPException(status_code=404, detail="Fusion track not found")
    
    if fusion_track.status != "SUCCESS":
        raise HTTPException(status_code=400, detail="Fusion track not ready for download")
    
    # Download the file from Google Drive
    from fastapi.responses import FileResponse
    import os
    from app.services.gdrive import gdrive_service
    
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_file_path = os.path.join(temp_dir, fusion_track.filename)
    try:
        gdrive_service.download_file(fusion_track.gdrive_file_id, temp_file_path)
        
        # Return the file as a response
        return FileResponse(
            path=temp_file_path,
            filename=fusion_track.filename,
            media_type="audio/wav"
        )
    finally:
        # Clean up the temporary file in a background task
        def cleanup_temp_file():
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
        background_tasks = BackgroundTasks()
        background_tasks.add_task(cleanup_temp_file)