from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Environment configuration for frog micro-service."""
    
    # API Configuration
    frog_api_key: str = "sk-frog_dev_demo"
    port: int = 8000
    
    # External Service Keys
    openai_key: Optional[str] = None
    
    # Security
    vault_key: Optional[str] = None  # 32-byte base64 for Fernet encryption
    
    # Database (future extension)
    database_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 