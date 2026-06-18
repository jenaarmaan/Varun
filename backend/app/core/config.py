import os
from typing import Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Project Varun"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_signing_key_for_testing_purposes")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Environment
    ENV: str = "development"  # development, staging, production
    
    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/varun"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/varun"
    
    # Redis & Cache Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_DEFAULT_TTL: int = 1800  # 30 minutes in seconds
    
    # GCP / Vertex AI Settings
    GCP_PROJECT_ID: str = "project-varun-dev"
    GCP_LOCATION: str = "asia-south1"  # Mumbai region
    GEMINI_MODEL: str = "gemini-2.5-pro"
    EMBEDDING_MODEL: str = "text-embedding-gecko"
    
    # Weather Reliability Settings
    WEATHER_FRESHNESS_LIMIT_HOURS: int = 6
    SOURCE_PRIORITY: Dict[str, int] = {
        "IMD": 1,
        "OpenMeteo": 2
    }
    
    # AI Grounding Confidence Safety Threshold
    SAFETY_CONFIDENCE_THRESHOLD: float = 0.85
    
    # SLO SLA Targets
    TARGET_AVAILABILITY: float = 99.9
    TARGET_P95_LATENCY_SEC: float = 5.0
    
    # File Storage
    STORAGE_QUARANTINE_DIR: str = "quarantine"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
