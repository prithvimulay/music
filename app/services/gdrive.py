# app/services/gdrive.py
import os
import io
import logging
from typing import Optional, BinaryIO, Dict, Any, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveService:
    def __init__(self):
        """Initialize Google Drive service using service account credentials"""
        logger.info("Initializing GoogleDriveService")
        # Path to the service account JSON file
        credentials_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "credentials", 
            "gdrive-credentials.json"
        )
        
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            logger.error(f"Google Drive credentials not found at {credentials_path}")
            raise FileNotFoundError(f"Google Drive service account credentials not found at {credentials_path}")
        
        # Create credentials from the service account file
        logger.info(f"Loading credentials from {credentials_path}")
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build the service
        logger.info("Building Google Drive service")
        self.service = build('drive', 'v3', credentials=credentials)
        logger.info("GoogleDriveService initialized successfully")
        
    def upload_file(self, file_content: BinaryIO, filename: str, mime_type: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to Google Drive and return file details"""
        logger.info(f"Uploading file: {filename} with mime type: {mime_type or 'audio/mpeg'}")
        file_metadata = {'name': filename}
        
        media = MediaIoBaseUpload(
            file_content,
            mimetype=mime_type or 'audio/mpeg',
            resumable=True
        )
        
        try:
            logger.info(f"Creating file in Google Drive: {filename}")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size'
            ).execute()
            
            # Set permissions to make file accessible via link
            logger.info(f"Setting permissions for file: {file['id']}")
            self.service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
            
            logger.info(f"File uploaded successfully: {file['id']}")
            return file
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
        
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        logger.info(f"Deleting file with ID: {file_id}")
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"File deleted successfully: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False
        
    def get_download_link(self, file_id: str) -> str:
        """Get a direct download link for a file"""
        logger.info(f"Generating download link for file: {file_id}")
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get metadata for a file"""
        logger.info(f"Getting metadata for file: {file_id}")
        try:
            metadata = self.service.files().get(
                fileId=file_id, 
                fields='id,name,mimeType,size'
            ).execute()
            logger.info(f"Retrieved metadata for file {file_id}: {metadata}")
            return metadata
        except Exception as e:
            logger.error(f"Error getting metadata for file {file_id}: {str(e)}")
            raise
        
    def test_connection(self) -> Dict[str, str]:
        """Test the connection to Google Drive API"""
        logger.info("Testing connection to Google Drive API")
        try:
            # List files to test connection
            files = self.service.files().list(pageSize=1).execute()
            logger.info("Successfully connected to Google Drive API")
            return {"status": "success", "message": "Connected to Google Drive API successfully"}
        except Exception as e:
            logger.error(f"Failed to connect to Google Drive API: {str(e)}")
            return {"status": "error", "message": f"Failed to connect: {str(e)}"}
            
    def download_file(self, file_id: str, destination_path: Optional[str] = None) -> Tuple[bool, str]:
        """Download a file from Google Drive to a local path
        
        Args:
            file_id: The ID of the file to download
            destination_path: The local path where the file should be saved. If None, will use the downloads folder.
            
        Returns:
            Tuple of (success, message)
        """
        # If no destination path provided, use downloads folder
        if destination_path is None:
            # Get file metadata to use original filename
            try:
                metadata = self.get_file_metadata(file_id)
                filename = metadata.get('name', f"file_{file_id}")
            except Exception:
                filename = f"file_{file_id}"
                
            # Create downloads directory in project root
            downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            destination_path = os.path.join(downloads_dir, filename)
            
        logger.info(f"Downloading file {file_id} to {destination_path}")
        try:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Get the file from Google Drive
            request = self.service.files().get_media(fileId=file_id)
            
            # Stream the file to disk
            with io.BytesIO() as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.info(f"Download progress: {int(status.progress() * 100)}%")
                
                # Write to file
                fh.seek(0)
                with open(destination_path, 'wb') as f:
                    f.write(fh.read())
            
            logger.info(f"File downloaded successfully to {destination_path}")
            return True, f"File downloaded successfully to {destination_path}"
            
        except Exception as e:
            error_msg = f"Error downloading file {file_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

gdrive_service = GoogleDriveService()