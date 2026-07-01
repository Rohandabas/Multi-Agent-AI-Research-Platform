"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # API Keys
    GOOGLE_API_KEY: str
    GEMINI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: str
    GROQ_API_KEY: Optional[str] = None

    # LLM
    LLM_PROVIDER: str = "gemini"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_MODEL: str = "models/text-embedding-004"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/research.db"

    # Vector store
    CHROMA_PATH: str = "./data/chroma"

    # Output paths
    OUTPUTS_PATH: str = "./outputs"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # CORS
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
