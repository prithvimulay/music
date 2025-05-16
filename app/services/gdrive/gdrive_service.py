# app/services/gdrive/gdrive_service.py
import os
import io
import logging
import mimetypes
from typing import Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)

# Path to the credentials file
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "credentials",
    "gdrive-credentials.json"
)

def get_credentials():
    """Get credentials for Google Drive API."""
    if not os.path.exists(CREDENTIALS_PATH):
        logger.error(f"Credentials file not found at {CREDENTIALS_PATH}")
        raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_PATH}")
    
    return service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=['https://www.googleapis.com/auth/drive']
    )

def get_file_metadata(file_id: str) -> Dict[str, Any]:
    """Get metadata for a file in Google Drive."""
    try:
        # Initialize the Google Drive API client
        credentials = get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='id,name,mimeType,size').execute()
        return file_metadata
    except Exception as e:
        logger.error(f"Error getting file metadata: {str(e)}")
        raise

def download_file(file_id: str, destination_path: str) -> str:
    """Download a file from Google Drive."""
    try:
        # Initialize the Google Drive API client
        credentials = get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # Create the destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Download the file
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            logger.info(f"Download {int(status.progress() * 100)}%")
        
        return destination_path
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise

def upload_file(file_path: str, name: str = None, mime_type: str = None) -> str:
    """Upload a file to Google Drive and return the file ID."""
    try:
        # Initialize the Google Drive API client
        credentials = get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # Create file metadata
        file_metadata = {
            'name': name or os.path.basename(file_path),
            'mimeType': mime_type or mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        }
        
        # Upload the file
        media = MediaFileUpload(file_path, 
                              mimetype=file_metadata['mimeType'],
                              resumable=True)
        
        file = service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
        
        return file.get('id')
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise

def test_connection() -> Dict[str, str]:
    """Test the connection to Google Drive."""
    try:
        credentials = get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # List files to test connection
        results = service.files().list(pageSize=1).execute()
        
        return {
            "status": "success",
            "message": "Connected to Google Drive API successfully"
        }
    except Exception as e:
        logger.error(f"Error connecting to Google Drive: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to connect to Google Drive API: {str(e)}"
        }