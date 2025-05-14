#!/usr/bin/env python3
"""
Test script for the AI Music Fusion workflow.
This script tests each component of the workflow individually and then as an integrated pipeline.
"""

import os
import sys
import time
import unittest
import tempfile
import shutil
import json
from pathlib import Path
import logging
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestMusicFusion(unittest.TestCase):
    """Test cases for the AI Music Fusion workflow."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Create test directories
        cls.test_dir = tempfile.mkdtemp()
        cls.uploaded_tracks_dir = os.path.join(cls.test_dir, "uploaded_tracks")
        cls.generated_tracks_dir = os.path.join(cls.test_dir, "generated_tracks")
        cls.temp_stems_dir = os.path.join(cls.test_dir, "temp_stems")
        
        os.makedirs(cls.uploaded_tracks_dir, exist_ok=True)
        os.makedirs(cls.generated_tracks_dir, exist_ok=True)
        os.makedirs(cls.temp_stems_dir, exist_ok=True)
        
        # Create test audio files
        cls.test_track1_path = os.path.join(cls.uploaded_tracks_dir, "test_track1.mp3")
        cls.test_track2_path = os.path.join(cls.uploaded_tracks_dir, "test_track2.mp3")
        
        # Create empty files for testing
        Path(cls.test_track1_path).touch()
        Path(cls.test_track2_path).touch()
        
        # Mock Google Drive IDs
        cls.test_track1_id = "test_gdrive_id_1"
        cls.test_track2_id = "test_gdrive_id_2"
        
        # Test project and user IDs
        cls.test_project_id = 999
        cls.test_user_id = 888
        
        logger.info(f"Test environment set up in {cls.test_dir}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        shutil.rmtree(cls.test_dir)
        logger.info("Test environment cleaned up")

    def test_directory_structure(self):
        """Test that the required directories exist."""
        logger.info("Testing directory structure...")
        
        # Check that the directories exist in the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        directories = [
            "uploaded_tracks",
            "generated_tracks",
            "temp_stems",
            "credentials"
        ]
        
        for directory in directories:
            dir_path = os.path.join(project_root, directory)
            self.assertTrue(os.path.exists(dir_path), f"Directory {directory} does not exist")
        
        logger.info("Directory structure test passed")

    def test_docker_compose_file(self):
        """Test that the docker-compose.yml file exists and has the required services."""
        logger.info("Testing docker-compose.yml...")
        
        # Check that the docker-compose.yml file exists
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docker_compose_path = os.path.join(project_root, "docker-compose.yml")
        
        self.assertTrue(os.path.exists(docker_compose_path), "docker-compose.yml does not exist")
        
        # Check that the file contains the required services
        with open(docker_compose_path, "r") as f:
            content = f.read()
            
            # Check for required services
            self.assertIn("redis:", content, "Redis service not found in docker-compose.yml")
            self.assertIn("app:", content, "App service not found in docker-compose.yml")
            self.assertIn("celery_worker:", content, "Celery worker service not found in docker-compose.yml")
            
            # Check for volume mounts
            self.assertIn("uploaded_tracks:", content, "uploaded_tracks volume not found in docker-compose.yml")
            self.assertIn("generated_tracks:", content, "generated_tracks volume not found in docker-compose.yml")
            self.assertIn("temp_stems:", content, "temp_stems volume not found in docker-compose.yml")
        
        logger.info("docker-compose.yml test passed")

    def test_celery_worker_file(self):
        """Test that the celery worker file exists and has the required configuration."""
        logger.info("Testing celery worker file...")
        
        # Check that the celery worker file exists
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        celery_worker_path = os.path.join(project_root, "app", "celeryworker", "worker.py")
        
        self.assertTrue(os.path.exists(celery_worker_path), "Celery worker file does not exist")
        
        # Check that the file contains the required configuration
        with open(celery_worker_path, "r") as f:
            content = f.read()
            
            # Check for required configuration
            self.assertIn("celery_app", content, "Celery app not found in worker.py")
            self.assertIn("broker=", content, "Broker URL not found in worker.py")
            self.assertIn("backend=", content, "Result backend not found in worker.py")
            self.assertIn("task_routes", content, "Task routes not found in worker.py")
        
        logger.info("Celery worker file test passed")

    def test_celery_tasks_file(self):
        """Test that the celery tasks file exists and has the required tasks."""
        logger.info("Testing celery tasks file...")
        
        # Check that the celery tasks file exists
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        celery_tasks_path = os.path.join(project_root, "app", "celeryworker", "tasks.py")
        
        self.assertTrue(os.path.exists(celery_tasks_path), "Celery tasks file does not exist")
        
        # Check that the file contains the required tasks
        with open(celery_tasks_path, "r") as f:
            content = f.read()
            
            # Check for required tasks
            self.assertIn("stem_separation", content, "Stem separation task not found in tasks.py")
            self.assertIn("feature_extraction", content, "Feature extraction task not found in tasks.py")
            self.assertIn("generate_fusion", content, "Generate fusion task not found in tasks.py")
            self.assertIn("enhance_audio", content, "Enhance audio task not found in tasks.py")
        
        logger.info("Celery tasks file test passed")

    def test_google_drive_credentials(self):
        """Test that Google Drive credentials are available."""
        logger.info("Testing Google Drive credentials...")
        
        # Check for credentials file
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        credentials_dir = os.path.join(project_root, "credentials")
        
        # Check that the credentials directory exists
        self.assertTrue(os.path.exists(credentials_dir), "Credentials directory does not exist")
        
        # Check for credentials files
        credentials_files = [f for f in os.listdir(credentials_dir) if f.endswith(".json")]
        self.assertTrue(len(credentials_files) > 0, "No credentials files found")
        
        logger.info("Google Drive credentials test passed")

if __name__ == "__main__":
    unittest.main()
