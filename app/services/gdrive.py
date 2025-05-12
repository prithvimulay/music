# app/services/gdrive.py
import os
from typing import Optional, BinaryIO, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

from app.core.config import settings

class GoogleDriveService:
    def __init__(self):
        """Initialize Google Drive service using service account credentials"""
        # Path to the service account JSON file
        credentials_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "credentials", 
            "gdrive-credentials.json"
        )
        
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Google Drive service account credentials not found at {credentials_path}")
        
        # Create credentials from the service account file
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build the service
        self.service = build('drive', 'v3', credentials=credentials)
        
    def upload_file(self, file_content: BinaryIO, filename: str, mime_type: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to Google Drive and return file details"""
        file_metadata = {'name': filename}
        
        media = MediaIoBaseUpload(
            file_content,
            mimetype=mime_type or 'audio/mpeg',
            resumable=True
        )
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,mimeType,size'
        ).execute()
        
        # Set permissions to make file accessible via link
        self.service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()
        
        return file
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception:
            return False
    
    def get_download_link(self, file_id: str) -> str:
        """Get a direct download link for a file"""
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get metadata for a file"""
        return self.service.files().get(
            fileId=file_id, 
            fields='id,name,mimeType,size'
        ).execute()
    
    def test_connection(self) -> Dict[str, str]:
        """Test the connection to Google Drive API"""
        try:
            # List files to test connection
            files = self.service.files().list(pageSize=1).execute()
            return {"status": "success", "message": "Connected to Google Drive API successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to connect: {str(e)}"}

gdrive_service = GoogleDriveService()