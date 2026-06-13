import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Document Fraud & Anomaly Detection API"
    API_V1_STR: str = "/api/v1"
    
    # Database
    # Use SQLite for hackathon simplicity, but easy to switch to PostgreSQL
    SQLALCHEMY_DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fraud_investigations.db")
    
    # Storage
    UPLOAD_DIR: str = "uploads"
    
    # AI Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    USE_LOCAL_GEMMA: bool = os.getenv("USE_LOCAL_GEMMA", "True").lower() == "true"
    
    # Trust Score Thresholds
    TRUST_THRESHOLD_AUTO_APPROVE: int = 85
    TRUST_THRESHOLD_HIGH_RISK_REJECT: int = 50
    CONFIDENCE_THRESHOLD_AUTO_APPROVE: int = 80

    class Config:
        case_sensitive = True

settings = Settings()
