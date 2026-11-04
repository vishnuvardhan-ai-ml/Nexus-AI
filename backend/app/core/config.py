"""
Core configuration settings for NEXUS AI Backend.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NEXUS AI - Community Intelligence & Risk Decision Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://nexus-ai.vercel.app",
    ]

    # Host & Port settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Firebase Admin SDK & Cloud Firestore configuration
    FIREBASE_PROJECT_ID: str = "nexus-ai-4a631"
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "secrets/firebase-service-account.json"
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    FIREBASE_USE_ADC: bool = False
    FIREBASE_STORAGE_BUCKET: Optional[str] = "nexus-ai-4a631.firebasestorage.app"
    FIRESTORE_DATABASE_ID: str = "(default)"
    
    # Emulators (optional for local offline testing)
    FIREBASE_AUTH_EMULATOR_HOST: Optional[str] = None
    FIRESTORE_EMULATOR_HOST: Optional[str] = None

    # Distributed Rate Limiting (Redis URL or Memory fallback)
    REDIS_URL: Optional[str] = None
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_AUTH: str = "20/minute"
    RATE_LIMIT_INCIDENT_WRITE: str = "10/minute"
    RATE_LIMIT_AI: str = "30/minute"
    RATE_LIMIT_GEO: str = "60/minute"

    # Reverse proxy trusted network list (e.g. Cloud Run, Render, GCP Cloud Load Balancer)
    TRUSTED_PROXIES: List[str] = ["127.0.0.1", "::1"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    def validate_production_security(self) -> None:
        """
        Fail closed if unsafe debug or wildcard configurations are active in production.
        """
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Production startup aborted because DEBUG is True. "
                    "Set DEBUG=False in production environment."
                )
            if "*" in self.BACKEND_CORS_ORIGINS:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Wildcard CORS origin '*' is strictly prohibited in production."
                )


settings = Settings()
