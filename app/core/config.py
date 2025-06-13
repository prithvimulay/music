from typing import List, Union, Optional
import json

# Version-compatible imports
try:
    # Try importing for Pydantic v1 (Docker environment)
    from pydantic import AnyHttpUrl, validator, BaseSettings
    PYDANTIC_V1 = True
except ImportError:
    # Fall back to Pydantic v2 imports (local environment)
    from pydantic import AnyHttpUrl, field_validator
    from pydantic_settings import BaseSettings
    PYDANTIC_V1 = False
    
    # Create compatibility layer for v1 style validators
    def validator(*fields, pre=False, **kwargs):
        # Map v1 validator params to v2 field_validator
        mode = 'before' if pre else 'after'
        return field_validator(*fields, mode=mode, **kwargs)

class Settings(BaseSettings):
    # API
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], values) -> str:
        if isinstance(v, str):
            return v
            
        # Handle different parameter types between Pydantic v1 and v2
        if PYDANTIC_V1:
            # In v1, values is a dict
            postgres_user = values.get('POSTGRES_USER')
            postgres_password = values.get('POSTGRES_PASSWORD')
            postgres_server = values.get('POSTGRES_SERVER')
            postgres_port = values.get('POSTGRES_PORT')
            postgres_db = values.get('POSTGRES_DB')
        else:
            # In v2, values is a data attribute
            postgres_user = values.data.get('POSTGRES_USER')
            postgres_password = values.data.get('POSTGRES_PASSWORD')
            postgres_server = values.data.get('POSTGRES_SERVER')
            postgres_port = values.data.get('POSTGRES_PORT')
            postgres_db = values.data.get('POSTGRES_DB')
        
        # Detect if running locally (not in Docker) and adjust server name
        # When running locally, we need to use localhost instead of container names
        import os
        if os.environ.get("RUNNING_LOCALLY") == "true" and postgres_server == "db":
            postgres_server = "localhost"
            
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int

    AUDIOCRAFT_CACHE_DIR: str = "/app/.cache"
    
    # Replicate API settings
    REPLICATE_API_TOKEN: str = ""
    REPLICATE_MODEL_ID: str = ""
    MUSICGEN_MODEL_ID: str = ""  # Keeping for backward compatibility
    
    if PYDANTIC_V1:
        class Config:
            case_sensitive = True
            env_file = ".env"
            extra = "ignore"  # This is key - it tells pydantic to ignore extra fields
    else:
        model_config = {
            "case_sensitive": True,
            "env_file": ".env",
            "extra": "ignore"  # This is key - it tells pydantic to ignore extra fields
        }
    
settings = Settings()