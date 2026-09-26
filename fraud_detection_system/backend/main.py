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

# Migration: ensure investigations table has is_baseline column if it already exists
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("investigations")]
    if "is_baseline" not in columns:
        logger.info("Migrating database: adding 'is_baseline' column to 'investigations' table...")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE investigations ADD COLUMN is_baseline BOOLEAN DEFAULT 0"))
        logger.info("Database migration complete.")
except Exception as e:
    logger.error(f"Failed to run is_baseline database migration: {e}")

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
    allow_credentials=False,
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

from fastapi.responses import Response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.api_route("/", methods=["GET", "HEAD"])
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


import time
import urllib.request
import json
import asyncio

from core.system_state import startup_time_log
from core.config import resolve_ollama_model

@app.on_event("startup")
def startup_event():
    """
    Check Ollama connectivity, verify the configured model exists,
    and warm up local LLM. Refuses to enter AI mode if the model is missing.
    """
    global startup_time_log
    start_t = time.time()
    logger.info("[STARTUP] Initializing Forensic Auditor checks...")
    
    if not settings.USE_LOCAL_LLM:
        logger.info("[STARTUP] Local LLM is disabled by configuration.")
        startup_time_log["ollama_status"] = "disabled"
        startup_time_log["reason"] = "Local LLM disabled by config"
        return
        
    target_model = settings.OLLAMA_MODEL
    url_tags = f"{settings.OLLAMA_BASE_URL}/api/tags"
    try:
        req = urllib.request.Request(url_tags)
        with urllib.request.urlopen(req, timeout=3.0) as response:
            if response.status == 200:
                res_body = response.read().decode('utf-8')
                res_data = json.loads(res_body)
                models = [m.get("name") for m in res_data.get("models", [])]
                logger.info(f"[STARTUP] Connected to Ollama. Installed models: {models}")
                
                # Verify required model exists, fall back to any installed model if not
                resolved_model = resolve_ollama_model(target_model, settings.OLLAMA_BASE_URL)
                model_ok = resolved_model != target_model or any(
                    target_model in m or m.startswith(target_model) for m in models
                )
                if resolved_model != target_model and models:
                    # Preferred not installed but a fallback was found
                    logger.warning(
                        f"\n\n[STARTUP_WARNING] REQUIRED MODEL '{target_model}' IS NOT LOADED!\n"
                        f"Auto-falling back to installed model '{resolved_model}'.\n"
                        f"Installed models: {models}\n"
                    )
                    settings.OLLAMA_MODEL = resolved_model
                    model_ok = True
                elif model_ok:
                    # Bind to the exact installed tag
                    for m in models:
                        if target_model in m or m.startswith(target_model):
                            settings.OLLAMA_MODEL = m
                            break
                        
                if not model_ok:
                    logger.warning(
                        f"\n\n[STARTUP_WARNING] REQUIRED MODEL '{target_model}' IS NOT LOADED!\n"
                        f"Please pull it: 'ollama pull {target_model}'\n"
                        f"AI mode will be disabled.\n"
                    )
                    startup_time_log["ollama_status"] = "connected"
                    startup_time_log["model"] = target_model
                    startup_time_log["ai"] = "offline"
                    startup_time_log["reason"] = f"{target_model} not loaded"
                else:
                    # Warmup model
                    logger.info(f"[STARTUP] Warming up Ollama model '{settings.OLLAMA_MODEL}'...")
                    url_gen = f"{settings.OLLAMA_BASE_URL}/api/generate"
                    payload = {
                        "model": settings.OLLAMA_MODEL,
                        "prompt": "ping",
                        "stream": False
                    }
                    try:
                        req_gen = urllib.request.Request(
                            url_gen,
                            data=json.dumps(payload).encode('utf-8'),
                            headers={'Content-Type': 'application/json'},
                            method='POST'
                        )
                        with urllib.request.urlopen(req_gen, timeout=settings.OLLAMA_WARMUP_TIMEOUT_SECONDS) as gen_res:
                            gen_res.read()
                            duration_ms = int((time.time() - start_t) * 1000)
                            logger.info(f"[STARTUP] Ollama warmup completed successfully in {duration_ms} ms.")
                            startup_time_log["warmup_duration_ms"] = duration_ms
                            startup_time_log["model"] = settings.OLLAMA_MODEL
                            startup_time_log["ollama_status"] = "connected"
                            startup_time_log["ai"] = "ready"
                            startup_time_log["warm"] = True
                            startup_time_log["reason"] = ""
                    except Exception as e:
                        logger.warning(f"[STARTUP] Pre-warming request timed out: {e}")
                        startup_time_log["ollama_status"] = "connected"
                        startup_time_log["model"] = settings.OLLAMA_MODEL
                        startup_time_log["ai"] = "ready"
                        startup_time_log["warm"] = False
                        startup_time_log["reason"] = "Warmup timed out"
            else:
                logger.warning("[STARTUP_WARNING] Ollama returned non-200 response.")
                startup_time_log["ollama_status"] = "offline"
                startup_time_log["ai"] = "offline"
                startup_time_log["reason"] = "Ollama tags check failed"
    except Exception as e:
        logger.warning(
            f"\n\n[STARTUP_WARNING] Could not connect to local Ollama service: {e}\n"
            f"If you plan to run local AI summaries, please start Ollama first (http://localhost:11434).\n"
        )
        startup_time_log["ollama_status"] = "offline"
        startup_time_log["ai"] = "offline"
        startup_time_log["reason"] = "Unable to connect to Ollama"

    from core.ai_provider_manager import ai_provider_manager
    ai_provider_manager.ensure_model_is_pulled()


@app.api_route("/api/v1/health", methods=["GET", "HEAD"])
def api_health():
    """Detailed health check for the API."""
    db_ok = True
    try:
        from sqlalchemy import text
        from core.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
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
