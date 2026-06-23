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
    background_tasks.add_task(investigation_manager.run_analysis, id)
    
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
