#!/usr/bin/env python3
"""
Test runner script for the AI Music Fusion workflow.
This script runs the tests and verifies that the Docker setup is working correctly.
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_directories():
    """Check that the required directories exist, create them if they don't."""
    logger.info("Checking required directories...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Define the directories to check
    directories = [
        "uploaded_tracks",
        "generated_tracks",
        "temp_stems",
        "credentials",
        "tests"
    ]
    
    # Check each directory
    for directory in directories:
        dir_path = os.path.join(project_root, directory)
        if not os.path.exists(dir_path):
            logger.info(f"Creating directory: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
        else:
            logger.info(f"Directory exists: {dir_path}")
    
    return True

def check_redis_connection():
    """Check that Redis is running and accessible."""
    logger.info("Checking Redis connection...")
    
    try:
        # Try to import Redis
        import redis
        
        # Try to connect to Redis
        redis_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        
        # Try to ping Redis
        if redis_client.ping():
            logger.info("Redis connection successful")
            return True
        else:
            logger.error("Redis ping failed")
            return False
    except ImportError:
        logger.error("Redis package not installed. Install it with 'pip install redis'")
        return False
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        return False

def check_celery():
    """Check that Celery is properly configured."""
    logger.info("Checking Celery configuration...")
    
    try:
        # Try to import Celery
        import celery
        from app.celeryworker.worker import celery_app
        
        # Check that Celery is configured
        broker_url = celery_app.conf.broker_url
        backend_url = celery_app.conf.result_backend
        
        logger.info(f"Celery broker URL: {broker_url}")
        logger.info(f"Celery result backend: {backend_url}")
        
        # Check that tasks are registered
        task_names = [
            "app.celeryworker.tasks.stem_separation",
            "app.celeryworker.tasks.feature_extraction",
            "app.celeryworker.tasks.generate_fusion",
            "app.celeryworker.tasks.enhance_audio",
            "app.celeryworker.tasks.cleanup_temp_files"
        ]
        
        missing_tasks = []
        for task_name in task_names:
            if task_name not in celery_app.tasks:
                missing_tasks.append(task_name)
        
        if missing_tasks:
            logger.error(f"Missing Celery tasks: {missing_tasks}")
            return False
        else:
            logger.info("All Celery tasks are registered")
            return True
    except ImportError:
        logger.error("Celery package not installed. Install it with 'pip install celery'")
        return False
    except Exception as e:
        logger.error(f"Celery check failed: {str(e)}")
        return False

def check_google_drive():
    """Check that Google Drive credentials are available."""
    logger.info("Checking Google Drive credentials...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Check for credentials file
    credentials_dir = os.path.join(project_root, "credentials")
    credentials_files = [f for f in os.listdir(credentials_dir) if f.endswith(".json")]
    
    if not credentials_files:
        logger.warning("No Google Drive credentials found. Place your credentials JSON file in the 'credentials' directory.")
        return False
    else:
        logger.info(f"Found credentials files: {credentials_files}")
        return True

def run_unittest_directly():
    """Run unittest directly using the unittest module."""
    logger.info("Running tests directly with unittest...")
    
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.abspath(__file__))
        test_file = os.path.join(project_root, "tests", "test_music_fusion.py")
        
        # Check if the test file exists
        if not os.path.exists(test_file):
            logger.error(f"Test file not found: {test_file}")
            return False
        
        # Run the tests using unittest
        result = subprocess.run(
            [sys.executable, "-m", "unittest", test_file],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Print the output
        logger.info(result.stdout.decode())
        
        if result.returncode == 0:
            logger.info("Tests passed!")
            return True
        else:
            logger.error("Tests failed")
            logger.error(result.stderr.decode())
            return False
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return False

def run_docker_tests():
    """Run tests in the Docker environment."""
    logger.info("Running tests in Docker environment...")
    
    try:
        # Run the tests in the Docker container
        result = subprocess.run(
            ["docker-compose", "exec", "app", "python", "-m", "unittest", "discover", "-s", "tests"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Print the output
        logger.info(result.stdout.decode())
        
        if result.returncode == 0:
            logger.info("Docker tests passed!")
            return True
        else:
            logger.error("Docker tests failed")
            logger.error(result.stderr.decode())
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker test command failed: {e}")
        logger.error(e.stderr.decode())
        return False
    except Exception as e:
        logger.error(f"Docker test failed: {str(e)}")
        return False

def check_docker():
    """Check that Docker is running and the required images are available."""
    logger.info("Checking Docker...")
    
    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Docker is running")
        
        # Check if Docker Compose is available
        subprocess.run(["docker-compose", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Docker Compose is available")
        
        return True
    except subprocess.CalledProcessError:
        logger.error("Docker check failed. Make sure Docker is running.")
        return False
    except FileNotFoundError:
        logger.error("Docker or Docker Compose not found. Make sure they are installed.")
        return False

def install_dependencies():
    """Install required Python dependencies."""
    logger.info("Installing required dependencies...")
    
    dependencies = [
        "redis",
        "celery",
        "pytest"
    ]
    
    for dependency in dependencies:
        try:
            logger.info(f"Installing {dependency}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", dependency],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"{dependency} installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {dependency}")
            logger.error(e.stderr.decode())
            return False
    
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run tests for the AI Music Fusion workflow")
    parser.add_argument("--docker", action="store_true", help="Run tests in Docker environment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--install", action="store_true", help="Install required dependencies")
    args = parser.parse_args()
    
    # Check directories
    if not check_directories():
        logger.error("Directory check failed")
        sys.exit(1)
    
    # Install dependencies if requested
    if args.install:
        if not install_dependencies():
            logger.error("Failed to install dependencies")
            sys.exit(1)
    
    if args.docker:
        # Check Docker
        if not check_docker():
            logger.error("Docker check failed")
            sys.exit(1)
        
        # Run tests in Docker
        if not run_docker_tests():
            logger.error("Docker tests failed")
            sys.exit(1)
    else:
        # Check Redis
        redis_ok = check_redis_connection()
        if not redis_ok:
            logger.warning("Redis connection failed. Some tests may fail.")
        
        # Check Celery
        celery_ok = check_celery()
        if not celery_ok:
            logger.warning("Celery check failed. Some tests may fail.")
        
        # Check Google Drive
        gdrive_ok = check_google_drive()
        if not gdrive_ok:
            logger.warning("Google Drive check failed. Some tests may fail.")
        
        # Run unit tests
        if not run_unittest_directly():
            logger.error("Unit tests failed")
            sys.exit(1)
    
    logger.info("All checks and tests passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
