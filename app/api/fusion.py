# app/api/endpoints/fusion.py
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from celery import chain
from celery.result import AsyncResult

from app.db.session import get_db
from app.db.models.audio_file import AudioFile
from app.db.models.user import User
from app.api.deps import get_current_user
from app.schemas.fusion import FusionRequest, FusionResponse, FusionStatus, FusionPrompt
from app.celeryworker.tasks import stem_separation, feature_extraction, generate_fusion, enhance_audio
import json

router = APIRouter()

@router.post("/fusion/prepare-prompt/", response_model=FusionPrompt)
async def prepare_fusion_prompt(
    fusion_request: FusionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    First step of fusion generation: Extract features and generate a prompt
    that the user can review and modify before starting the actual fusion.
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
    
    # Start only the stem separation and feature extraction tasks
    task = chain(
        stem_separation.s(track1.gdrive_file_id, track2.gdrive_file_id, 
                         fusion_request.project_id, current_user.id),
        feature_extraction.s()
    )
    
    result = task.apply_async()
    
    # Wait for the result (this is synchronous but acceptable for the first step)
    feature_data = result.get(timeout=300)  # 5 minute timeout
    
    # Create a prompt based on extracted features
    track1_features = feature_data["features"]["track1"]
    track2_features = feature_data["features"]["track2"]
    
    # Calculate target tempo (average of the two tracks)
    target_tempo = (track1_features["tempo"] + track2_features["tempo"]) / 2
    
    # Create a descriptive prompt for MusicGen
    prompt = f"Create a fusion track with tempo {target_tempo:.1f} BPM, "
    prompt += f"combining the energy of track 1 ({track1_features['energy']:.2f}) and "
    prompt += f"the danceability of track 2 ({track2_features['danceability']:.2f}). "
    
    # Return the prompt and feature data to the user
    return {
        "generated_prompt": prompt,
        "track1_id": fusion_request.track1_id,
        "track2_id": fusion_request.track2_id,
        "project_id": fusion_request.project_id,
        "feature_data": feature_data
    }

@router.post("/fusion/generate/", response_model=FusionResponse)
async def generate_fusion_track(
    fusion_request: FusionRequest,
    feature_data_json: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a fusion track from two existing tracks."""
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
    
    # Check if we're continuing from prepare-prompt endpoint
    if feature_data_json:
        try:
            feature_data = json.loads(feature_data_json)
            
            # Start the fusion generation with the existing feature data
            task = chain(
                generate_fusion.s(feature_data, 
                                  duration=fusion_request.duration,
                                  temperature=fusion_request.temperature,
                                  prompt_guidance=fusion_request.prompt_guidance,
                                  custom_prompt=fusion_request.custom_prompt),
                enhance_audio.s()
            )
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid feature data format")
    else:
        # Start the full fusion task chain
        task = chain(
            stem_separation.s(track1.gdrive_file_id, track2.gdrive_file_id, 
                             fusion_request.project_id, current_user.id),
            feature_extraction.s(),
            generate_fusion.s(duration=fusion_request.duration,
                              temperature=fusion_request.temperature,
                              prompt_guidance=fusion_request.prompt_guidance,
                              custom_prompt=fusion_request.custom_prompt),
            enhance_audio.s()
        )
    
    result = task.apply_async()
    
    # Create a pending fusion record
    fusion_track = AudioFile(
        filename=f"fusion_pending_{result.id}.wav",
        status="PENDING",
        project_id=fusion_request.project_id,
        user_id=current_user.id,
        is_fusion=True,
        source_track1_id=track1.id,
        source_track2_id=track2.id,
        task_id=result.id
    )
    
    db.add(fusion_track)
    db.commit()
    db.refresh(fusion_track)
    
    return {
        "id": fusion_track.id,
        "status": fusion_track.status,
        "task_id": result.id
    }

@router.get("/fusion/status/{fusion_id}", response_model=FusionStatus)
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
    
    # If the track has a task_id, check the task status
    if fusion_track.task_id:
        task_result = AsyncResult(fusion_track.task_id)
        
        # Update the status in the database if needed
        if task_result.state != fusion_track.status:
            fusion_track.status = task_result.state
            db.commit()
            db.refresh(fusion_track)
    
    return {
        "id": fusion_track.id,
        "status": fusion_track.status,
        "filename": fusion_track.filename,
        "created_at": fusion_track.created_at
    }

@router.get("/fusion/download/{fusion_id}")
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