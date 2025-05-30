import os
from pydantic_settings import BaseSettings
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
    
    # OpenRouter integration
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Default model settings
    default_model: str = "openai/gpt-4o-mini"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 