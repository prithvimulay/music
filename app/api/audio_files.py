# app/api/audio_files.py
from typing import List, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Path, Query
from sqlalchemy.orm import Session
import io

from app.schemas.audio_file import AudioFile
from app.api.auth import get_current_active_user
from app.db.models.user import User as UserModel
from app.db.models.project import Project as ProjectModel
from app.db.models.audio_file import AudioFile as AudioFileModel
from app.db.session import get_db
from app.services.gdrive import gdrive_service

router = APIRouter()

@router.post("/upload", response_model=AudioFile)
async def upload_audio_file(
    *,
    db: Session = Depends(get_db),
    proj_id: int = Query(..., description="Project ID"), # Make proj_id required
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """Upload audio file to Google Drive and save metadata"""
    # The proj_id is now required and used directly

    # Check if project exists and belongs to user
    project = db.query(ProjectModel).filter(
        ProjectModel.id == proj_id, # Use proj_id directly
        ProjectModel.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have access"
        )

    # Validate file format
    allowed_formats = ["audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3"]
    if file.content_type not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File format not supported. Please upload WAV or MP3 files only and not {file.content_type}"
        )

    # Read file content to check size
    file_content = await file.read()

    # Validate file size (max 10MB for optimal processing with MusicGen small model)
    max_size_bytes = 10 * 1024 * 1024  # 10MB
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large - ({len(file_content)}). Maximum size is 10MB for optimal processing."
        )

    # Upload to Google Drive
    gdrive_file = gdrive_service.upload_file(
        io.BytesIO(file_content),
        file.filename,
        file.content_type
    )

    # Save file metadata to database
    audio_file = AudioFileModel(
        filename=file.filename,
        gdrive_file_id=gdrive_file['id'],
        file_size=int(gdrive_file.get('size', 0)),
        mime_type=gdrive_file.get('mimeType'),
        proj_id=proj_id, # Use proj_id directly
        user_id=current_user.id
    )

    db.add(audio_file)
    db.commit()
    db.refresh(audio_file)
    return audio_file

@router.get("/project/{proj_id}", response_model=List[AudioFile])
def get_project_audio_files(
    *,
    db: Session = Depends(get_db),
    proj_id: int = Path(..., title="Project ID"),
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """Get all audio files for a project"""
    # Check if project exists and belongs to user
    project = db.query(ProjectModel).filter(
        ProjectModel.id == proj_id,
        ProjectModel.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have access"
        )

    audio_files = db.query(AudioFileModel).filter(
        AudioFileModel.proj_id == proj_id
    ).all()

    return audio_files

@router.get("/{file_id}", response_model=AudioFile)
def get_audio_file(
    *,
    db: Session = Depends(get_db),
    file_id: int,
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """Get audio file by ID"""
    audio_file = db.query(AudioFileModel).filter(
        AudioFileModel.id == file_id,
        AudioFileModel.user_id == current_user.id
    ).first()

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    return audio_file

@router.get("/{file_id}/download-link")
def get_download_link(
    *,
    db: Session = Depends(get_db),
    file_id: int,
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """Get download link for audio file"""
    audio_file = db.query(AudioFileModel).filter(
        AudioFileModel.id == file_id,
        AudioFileModel.user_id == current_user.id
    ).first()

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    download_link = gdrive_service.get_download_link(audio_file.gdrive_file_id)
    return {"download_link": download_link}

# Add this to app/api/audio_files.py
@router.get("/test-gdrive-connection", tags=["test"])
def test_gdrive_connection(
    current_user: UserModel = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Test the Google Drive API connection"""
    return gdrive_service.test_connection()

@router.delete("/{file_id}", response_model=AudioFile)
def delete_audio_file(
    *,
    db: Session = Depends(get_db),
    file_id: int,
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """Delete audio file"""
    audio_file = db.query(AudioFileModel).filter(
        AudioFileModel.id == file_id,
        AudioFileModel.user_id == current_user.id
    ).first()

    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    # Delete from Google Drive
    gdrive_service.delete_file(audio_file.gdrive_file_id)

    # Delete from database
    db.delete(audio_file)
    db.commit()
    return audio_file