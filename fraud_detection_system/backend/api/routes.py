from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from core.database import get_db
from models import domain, database
from services.event_logger import log_event
from layers.intake import document_manager
from services.investigation_manager import investigation_manager
from services.report_generator import report_generator
import uuid
import os

router = APIRouter()

def _run_analysis_background(investigation_id: str) -> None:
    """
    Runs the async investigation pipeline inside Starlette's sync background
    threadpool so CPU/OCR/LLM work does not block status polling endpoints.
    """
    import asyncio
    asyncio.run(investigation_manager.run_analysis(investigation_id))

@router.get("/investigations", response_model=List[domain.InvestigationSchema])
def list_investigations(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Returns a list of investigations for the dashboard.
    Supports pagination and sorts by created date descending.
    """
    investigations = db.query(database.Investigation)\
        .order_by(database.Investigation.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return investigations

@router.post("/investigations", response_model=domain.InvestigationSchema, status_code=201)
def create_investigation(
    investigation: domain.InvestigationCreate,
    db: Session = Depends(get_db)
):
    db_investigation = database.Investigation(
        context=investigation.context,
        title=investigation.title or f"Investigation: {investigation.context}",
        status="PENDING",
        progress=0,
        current_stage="CREATED"
    )
    db.add(db_investigation)
    db.commit()
    db.refresh(db_investigation)
    
    log_event(
        db, 
        db_investigation.id, 
        "INVESTIGATION_CREATED", 
        f"Investigation created: {db_investigation.title}"
    )
    
    return db_investigation

@router.post("/investigations/{id}/documents", status_code=201)
def upload_documents(
    id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    uploaded_files = []
    for file in files:
        storage_path = document_manager.save_upload_file(file, id)
        doc = document_manager.add_document_to_db(
            db, id, file.filename, file.content_type, storage_path
        )
        uploaded_files.append(file.filename)
        log_event(
            db, 
            id, 
            "DOCUMENT_UPLOADED", 
            f"Document uploaded: {file.filename}",
            metadata={"document_id": doc.id}
        )
    
    return {"uploaded": uploaded_files}

@router.post("/investigations/{id}/analyze", status_code=202)
async def analyze_investigation(
    id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if not investigation.documents:
        raise HTTPException(status_code=400, detail="No documents uploaded for this investigation")

    # Start the async pipeline
    background_tasks.add_task(_run_analysis_background, id)
    
    return {"status": "PROCESSING", "message": "Analysis started in background"}

@router.get("/investigations/{id}/status", response_model=domain.InvestigationStatusSchema)
def get_investigation_status(id: str, db: Session = Depends(get_db)):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    message = None
    if investigation.status == "FAILED" and investigation.ai_summary_json:
        message = investigation.ai_summary_json.get("error")

    return {
        "status": investigation.status,
        "progress": investigation.progress,
        "current_stage": investigation.current_stage,
        "message": message
    }

@router.get("/investigations/{id}/results")
def get_investigation_results(id: str, db: Session = Depends(get_db)):
    """
    Returns all data for the investigation dashboard.
    """
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    return report_generator.generate_json_report(investigation)

@router.get("/investigations/{id}/report")
def download_investigation_report(id: str, db: Session = Depends(get_db)):
    """
    Generates and returns the downloadable forensic PDF report.
    """
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Report is only available for completed investigations")
        
    pdf_bytes = report_generator.generate_pdf_report(investigation)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Anobis_Report_{id}.pdf"
        }
    )

@router.get("/investigations/{id}/documents/{doc_id}/file")
def get_document_file(id: str, doc_id: str, db: Session = Depends(get_db)):
    """
    Serves the actual physical file of an uploaded document.
    """
    doc = db.query(database.Document).filter(
        database.Document.investigation_id == id,
        database.Document.id == doc_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=404, detail="Physical document file not found")
        
    media_type = "application/pdf" if doc.file_type == "pdf" else (doc.file_type or "application/octet-stream")
    return FileResponse(doc.storage_path, media_type=media_type)

@router.get("/investigations/{id}", response_model=domain.InvestigationFullSchema)
def get_investigation(id: str, db: Session = Depends(get_db)):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    return investigation

@router.get("/investigations/{id}/events", response_model=List[domain.InvestigationEventSchema])
def get_investigation_events(id: str, db: Session = Depends(get_db)):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    return investigation.events


@router.post("/investigations/{id}/approve-reference")
def approve_reference(id: str, db: Session = Depends(get_db)):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if investigation.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Only completed investigations can be approved as references")

    from layers.scoring.similarity_engine import similarity_engine
    from trusted_repository.repository_manager import repository_manager

    features = similarity_engine.generate_feature_vector(db, investigation)
    repository_manager.add_entry(
        features=features,
        metadata={
            "investigation_id": investigation.id,
            "title": investigation.title or f"Investigation: {investigation.context}",
            "context": investigation.context,
            "approved_at": investigation.updated_at.isoformat() if investigation.updated_at else None,
            "document_count": len(investigation.documents),
        }
    )
        
    log_event(
        db,
        id,
        "REFERENCE_APPROVED",
        "This case was manually approved and committed to the local forensic reference repository as a trusted baseline."
    )
    return {"status": "SUCCESS", "message": "Forensic pattern committed to local reference repository!"}


@router.post("/investigations/{id}/toggle-baseline")
def toggle_baseline(id: str, db: Session = Depends(get_db)):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if investigation.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Only completed investigations can be added to the baseline")

    from layers.scoring.similarity_engine import similarity_engine
    from trusted_repository.repository_manager import repository_manager

    # Toggle the boolean
    investigation.is_baseline = not getattr(investigation, "is_baseline", False)
    db.commit()

    if investigation.is_baseline:
        features = similarity_engine.generate_feature_vector(db, investigation)
        repository_manager.add_entry(
            features=features,
            metadata={
                "investigation_id": investigation.id,
                "title": investigation.title or f"Investigation: {investigation.context}",
                "context": investigation.context,
                "approved_at": investigation.updated_at.isoformat() if investigation.updated_at else None,
                "document_count": len(investigation.documents),
            }
        )
        log_event(
            db,
            id,
            "REFERENCE_APPROVED",
            "This case was committed to the local forensic reference repository as a trusted baseline."
        )
    else:
        repository_manager.remove_entry(investigation.id)
        log_event(
            db,
            id,
            "REFERENCE_REMOVED",
            "This case was removed from the local forensic reference repository."
        )

    return {"status": "SUCCESS", "is_baseline": investigation.is_baseline}


@router.delete("/investigations/{id}", status_code=204)
def delete_investigation(id: str, db: Session = Depends(get_db)):
    investigation = db.query(database.Investigation).filter(database.Investigation.id == id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
        
    # Also remove from trusted repository if it is there
    if getattr(investigation, "is_baseline", False):
        from trusted_repository.repository_manager import repository_manager
        repository_manager.remove_entry(investigation.id)

    db.delete(investigation)
    db.commit()
    return Response(status_code=204)


@router.post("/system/warmup")
def warmup_llm():
    """
    Manually triggers LLM pre-warming if local Ollama is the active provider.
    """
    from core.config import settings
    from core.settings_store import settings_store
    from core.ai_provider_manager import ai_provider_manager
    import urllib.request
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    execution_mode, provider, model, endpoint = ai_provider_manager.get_active_config()
    
    if provider == "Gemini API":
        return {"status": "SKIPPED", "message": "Warmup not required for cloud-hosted Gemini API."}
        
    url = f"{endpoint}/api/generate"
    payload = {
        "model": model,
        "prompt": "ping",
        "stream": False
    }
    
    try:
        req_gen = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req_gen, timeout=settings.OLLAMA_WARMUP_TIMEOUT_SECONDS) as response:
            response.read()
            return {"status": "SUCCESS", "message": f"Warmup completed. Model {model} loaded on Ollama."}
    except Exception as e:
        logger.warning(f"Ollama warmup request failed: {e}")
        return {"status": "TIMEOUT", "message": "Warmup request timed out or failed."}


@router.get("/system/health")
def get_system_health(db: Session = Depends(get_db)):
    """
    Returns complete forensic system health check.
    """
    from core.config import settings
    from core.settings_store import settings_store
    from core.ai_provider_manager import ai_provider_manager
    import urllib.request
    import json
    import os
    
    # 1. Database status
    db_ok = True
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
        
    # 2. Uploads directory check
    uploads_ok = os.path.exists(settings.UPLOAD_DIR)
    
    # 3. AI provider readiness status
    is_ready, err_msg = ai_provider_manager.is_ai_ready()
    ai_status = "ready" if is_ready else "offline"
    
    execution_mode, provider, model, endpoint = ai_provider_manager.get_active_config()
    
    # 4. OCR status (tesseract check)
    ocr_status = "ready"
    try:
        import pytesseract
        # Quick check if binary exists
        pytesseract.get_tesseract_version()
    except Exception:
        ocr_status = "unavailable"
        
    # 5. Dataset status
    dataset_status = "loaded"
    ref_dir = os.path.join(settings.DATASET_DIR, "reference")
    if not os.path.exists(ref_dir) or len(os.listdir(ref_dir)) == 0:
        dataset_status = "empty"

    from core.system_state import startup_time_log

    latency = ai_provider_manager.last_latency_ms if ai_provider_manager.last_latency_ms > 0 else startup_time_log.get("warmup_duration_ms", 0)

    return {
        "backend": "healthy" if db_ok and uploads_ok else "degraded",
        "database": "healthy" if db_ok else "disconnected",
        "ocr": "ready" if ocr_status == "ready" else "unavailable",
        "dataset": dataset_status,
        "knn": "ready" if dataset_status == "loaded" else "offline",
        "ollama": "ready" if provider == "Local Ollama" and is_ready else "offline",
        "model": model,
        "provider": provider,
        "endpoint": endpoint,
        "execution_mode": execution_mode,
        "ai": ai_status,
        "ai_mode": settings_store.get("ai_mode", "offline"),
        "gemini_configured": bool(settings_store.get("gemini_api_key", "")),
        "warm": startup_time_log.get("warm", False),
        "startup_latency_ms": latency,
        "reason": err_msg
    }


@router.get("/system/settings")
def get_settings():
    """
    Retrieves current Anobis settings.
    """
    from core.settings_store import settings_store
    return settings_store.all


@router.post("/system/settings")
def save_settings(settings: dict):
    """
    Updates and saves settings configuration.
    """
    from core.settings_store import settings_store
    from core.ai_provider_manager import ai_provider_manager
    result = settings_store.save(settings)
    # Invalidate AI readiness cache so model/provider changes are re-verified
    ai_provider_manager.invalidate_cache()
    return result


@router.post("/system/reindex-reference")
def reindex_reference_library(db: Session = Depends(get_db)):
    """
    Rebuilds the local trusted reference repository from completed baseline cases.
    """
    from layers.scoring.similarity_engine import similarity_engine
    from trusted_repository.repository_manager import repository_manager
    from datetime import datetime

    completed_baselines = db.query(database.Investigation).filter(
        database.Investigation.status == "COMPLETED",
        database.Investigation.is_baseline == True
    ).all()

    for investigation in completed_baselines:
        features = similarity_engine.generate_feature_vector(db, investigation)
        repository_manager.add_entry(
            features=features,
            metadata={
                "investigation_id": investigation.id,
                "title": investigation.title or f"Investigation: {investigation.context}",
                "context": investigation.context,
                "approved_at": datetime.utcnow().isoformat(),
                "document_count": len(investigation.documents),
            }
        )

    return {
        "status": "SUCCESS",
        "message": f"Reference library indexed from {len(completed_baselines)} approved baseline investigation(s).",
        "indexed": len(completed_baselines)
    }


@router.post("/system/flush-ocr-cache")
def flush_ocr_cache():
    """
    Clears cached OCR extraction artifacts.
    """
    import shutil
    cache_dir = os.path.join("uploads", "ocr_cache")
    removed = 0
    if os.path.exists(cache_dir):
        for name in os.listdir(cache_dir):
            path = os.path.join(cache_dir, name)
            if os.path.isfile(path):
                os.remove(path)
                removed += 1
            elif os.path.isdir(path):
                shutil.rmtree(path)
                removed += 1
    os.makedirs(cache_dir, exist_ok=True)
    return {"status": "SUCCESS", "message": f"OCR cache cleared ({removed} artifact(s) removed).", "removed": removed}
