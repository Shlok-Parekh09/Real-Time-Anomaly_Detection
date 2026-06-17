"""
Anobis — Offline Anomaly Detection API
Main entry point for the FastAPI application.
Supports:
  - POST /api/v1/investigate — Upload a single document for instant forensic analysis
  - Full CRUD Investigation endpoints via /api/v1/ router
  - Health check at /
  - Static file serving for uploaded documents
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from services.investigation_manager import InvestigationManager
from models.domain import InvestigationResponse
from core.database import engine, Base
from core.config import settings
import tempfile
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Anobis — Document Fraud & Anomaly Detection API",
    description=(
        "Air-gapped forensic document analysis engine. "
        "Analyzes PDFs and images for metadata manipulation, font inconsistencies, "
        "mathematical errors, pixel-level tampering, and more — all locally, no cloud APIs."
    ),
    version="2.0.0"
)

# CORS — allow all origins for local dev and web deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Serve uploaded files as static files (for frontend preview)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Register the CRUD investigation router
from api.routes import router as investigation_router
app.include_router(investigation_router, prefix=settings.API_V1_STR, tags=["Investigations"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Direct Analysis Endpoint (Quick single-file analysis)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/")
def health_check():
    """Health check endpoint."""
    return {
        "status": "online",
        "engine": "Anobis Forensic Analysis Engine",
        "version": "2.0.0",
        "capabilities": [
            "pdf_metadata_forensics",
            "pdf_structure_analysis",
            "font_consistency_analysis",
            "digital_signature_validation",
            "financial_math_validation",
            "running_balance_verification",
            "date_validation",
            "image_pixel_forensics",
            "ai_summary_generation"
        ]
    }


@app.post("/api/v1/investigate", response_model=InvestigationResponse)
async def investigate_document(file: UploadFile = File(...)):
    """
    Upload a single PDF or image file for instant forensic analysis.
    Returns fraud probability score, status, anomalies, and AI summary.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed_extensions = ('.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save uploaded file to a temporary location for local libraries to process
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        logger.info(f"[API] Starting analysis of '{file.filename}' ({len(content)} bytes)")
        manager = InvestigationManager()
        result = await manager.process_document(temp_path, file.filename)
        logger.info(f"[API] Analysis complete: score={result.fraud_probability_score}, status={result.status}")
        return result
    except Exception as e:
        logger.error(f"[API] Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal Forensic Engine Error: {str(e)}"
        )
    finally:
        # Ensure cleanup of sensitive files immediately after processing
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/api/v1/health")
def api_health():
    """Detailed health check for the API."""
    # Check database connectivity
    db_ok = True
    try:
        from core.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception:
        db_ok = False

    # Check if Ollama is available
    ollama_ok = False
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        response = urllib.request.urlopen(req, timeout=2)
        ollama_ok = response.status == 200
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "ollama_llm": "available" if ollama_ok else "unavailable (using template fallback)",
        "forensic_layers": {
            "pdf_metadata": True,
            "pdf_structure": True,
            "font_analysis": True,
            "digital_signature": True,
            "financial_validation": True,
            "balance_verification": True,
            "date_validation": True,
            "image_forensics": True,
            "ai_summary": True
        }
    }
