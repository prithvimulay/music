from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
import json

class Settings(BaseSettings):
    # API
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
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

    SQLALCHEMY_DATABASE_URI: str | None = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode='before')
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> str:
        if isinstance(v, str):
            return v
        return f"postgresql://{info.data.get('POSTGRES_USER')}:{info.data.get('POSTGRES_PASSWORD')}@{info.data.get('POSTGRES_SERVER')}:{info.data.get('POSTGRES_PORT')}/{info.data.get('POSTGRES_DB')}"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"  # This is key - it tells pydantic to ignore extra fields
    }
    
settings = Settings()