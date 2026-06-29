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


@router.post("/system/warmup")
def warmup_llm():
    """
    Warms up the Ollama local model to preload tokenizers and models in memory.
    """
    from core.config import settings
    import urllib.request
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    if not settings.USE_LOCAL_LLM:
        return {"status": "SKIPPED", "message": "Local LLM is disabled"}
        
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": "ping",
        "stream": False
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=settings.OLLAMA_WARMUP_TIMEOUT_SECONDS) as response:
            res_body = response.read().decode('utf-8')
            res_data = json.loads(res_body)
            return {"status": "SUCCESS", "message": f"Warmup completed. Model {settings.OLLAMA_MODEL} loaded."}
    except Exception as e:
        logger.warning(f"Ollama warmup request timed out/failed: {e}")
        return {"status": "TIMEOUT", "message": "Warmup request dispatched."}


@router.get("/system/health")
def get_system_health(db: Session = Depends(get_db)):
    """
    Returns complete forensic system health check.
    """
    from core.config import settings
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
    
    # 3. Ollama check & loaded model
    ollama_status = "offline"
    loaded_model = "None"
    
    if settings.USE_LOCAL_LLM:
        try:
            # Check model list in Ollama
            url = f"{settings.OLLAMA_BASE_URL}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    ollama_status = "ready"
                    res_body = response.read().decode('utf-8')
                    res_data = json.loads(res_body)
                    models = [m.get("name") for m in res_data.get("models", [])]
                    # Check if the configured model exists in Ollama
                    if settings.OLLAMA_MODEL in models or any(settings.OLLAMA_MODEL in m for m in models):
                        loaded_model = settings.OLLAMA_MODEL
                    elif models:
                        loaded_model = f"{settings.OLLAMA_MODEL} (Not Installed, Found: {', '.join(models)})"
                    else:
                        loaded_model = "No models installed"
        except Exception:
            ollama_status = "offline"
            
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

    return {
        "backend": "healthy" if db_ok and uploads_ok else "degraded",
        "database": "healthy" if db_ok else "disconnected",
        "ocr": "ready" if ocr_status == "ready" else "unavailable",
        "dataset": "loaded" if dataset_status == "loaded" else "empty",
        "knn": "ready" if dataset_status == "loaded" else "offline",
        "ollama": startup_time_log.get("ollama_status", "offline"),
        "model": startup_time_log.get("model", "gemma4:e4b"),
        "ai": startup_time_log.get("ai", "offline"),
        "warm": startup_time_log.get("warm", False),
        "startup_latency_ms": startup_time_log.get("warmup_duration_ms", 0)
    }
