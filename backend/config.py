"""
Configuration module for Language Coach backend
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Ollama Configuration
    ollama_url: str = "http://localhost:11434"
    model_name: str = "llama2:13b"
    
    # Database Configuration
    db_path: str = "../data/language_coach.db"
    
    # Scheduler Configuration
    auto_generate_time: str = "07:30"
    timezone: str = "Asia/Taipei"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    cache_expire: int = 3600  # 1 hour

    # AI Models Configuration
    small_model_name: str = "llama3:8b"
    large_model_name: str = "llama2:13b"
    
    # RAG Configuration
    chroma_db_path: str = "../data/chroma_db"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
