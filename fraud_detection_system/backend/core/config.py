import os
from pathlib import Path
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parents[1]

class Settings(BaseSettings):
    PROJECT_NAME: str = "Anobis — Document Fraud & Anomaly Detection API"
    API_V1_STR: str = "/api/v1"
    
    # Database
    SQLALCHEMY_DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fraud_investigations.db")
    
    # Storage
    UPLOAD_DIR: str = "uploads"
    DATASET_DIR: str = os.getenv("DATASET_DIR", str(PROJECT_ROOT / "dataset"))
    
    # AI / LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    USE_LOCAL_LLM: bool = os.getenv("USE_LOCAL_LLM", "True").lower() == "true"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
    OLLAMA_WARMUP_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_WARMUP_TIMEOUT_SECONDS", "120"))
    OLLAMA_GENERATE_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_GENERATE_TIMEOUT_SECONDS", "180"))
    OLLAMA_REVIEW_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_REVIEW_TIMEOUT_SECONDS", "120"))
    ENABLE_AI_SELF_REVIEW: bool = os.getenv("ENABLE_AI_SELF_REVIEW", "False").lower() == "true"
    
    # Trust Score Thresholds
    TRUST_THRESHOLD_AUTO_APPROVE: int = 85
    TRUST_THRESHOLD_HIGH_RISK_REJECT: int = 50
    CONFIDENCE_THRESHOLD_AUTO_APPROVE: int = 80

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    class Config:
        case_sensitive = True

settings = Settings()
