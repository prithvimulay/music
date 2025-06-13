"""
Fix script to install a compatible version of tokenizers for transformers.
"""
import subprocess
import sys
import pkg_resources

def fix_tokenizers():
    """Install a compatible version of tokenizers."""
    print("Checking current versions...")
    
    # Check transformers version
    transformers_version = pkg_resources.get_distribution("transformers").version
    print(f"Transformers version: {transformers_version}")
    
    # Uninstall current tokenizers
    print("Uninstalling current tokenizers...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "tokenizers"])
    
    # Install compatible version
    print("Installing tokenizers version 0.15.0...")
    subprocess.run([sys.executable, "-m", "pip", "install", "tokenizers==0.15.0"])
    
    # Verify installation
    try:
        tokenizers_version = pkg_resources.get_distribution("tokenizers").version
        print(f"Installed tokenizers version: {tokenizers_version}")
        print("\nNow testing if transformers can use tokenizers...")
        
        # Test importing
        from transformers import AutoTokenizer
        print("Successfully imported AutoTokenizer")
        
        print("\nTokenizers fixed successfully. Please restart the Celery worker.")
    except Exception as e:
        print(f"Error after installation: {str(e)}")

if __name__ == "__main__":
    fix_tokenizers()
