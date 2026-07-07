import os
import json
import logging
import urllib.request
from pathlib import Path
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parents[1]


def list_ollama_models(base_url: str = "http://localhost:11434", timeout: float = 1.5):
    """Return the list of model names installed in the local Ollama service.
    Returns an empty list if Ollama is unreachable."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        pass
    return []


def resolve_ollama_model(preferred: str, base_url: str = "http://localhost:11434") -> str:
    """Return the preferred model if installed, otherwise fall back to any
    available installed model. Returns `preferred` unchanged if Ollama is
    unreachable (so the caller can decide how to handle the mismatch)."""
    installed = list_ollama_models(base_url)
    if not installed:
        return preferred
    if preferred in installed or any(m.startswith(preferred) for m in installed):
        # Bind to the exact installed tag
        for m in installed:
            if m == preferred or m.startswith(preferred):
                return m
        return preferred
    # Preferred model not installed — fall back to the first available model
    fallback = installed[0]
    logger.warning(
        f"[OLLAMA] Preferred model '{preferred}' not installed. "
        f"Falling back to '{fallback}'. Installed: {installed}"
    )
    return fallback


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
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
    OLLAMA_WARMUP_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_WARMUP_TIMEOUT_SECONDS", "300"))
    OLLAMA_GENERATE_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_GENERATE_TIMEOUT_SECONDS", "600"))
    OLLAMA_REVIEW_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_REVIEW_TIMEOUT_SECONDS", "300"))
    ENABLE_AI_SELF_REVIEW: bool = os.getenv("ENABLE_AI_SELF_REVIEW", "False").lower() == "true"
    
    # Trust Score Thresholds
    TRUST_THRESHOLD_AUTO_APPROVE: int = 85
    TRUST_THRESHOLD_HIGH_RISK_REJECT: int = 50

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))

    class Config:
        case_sensitive = True

settings = Settings()
