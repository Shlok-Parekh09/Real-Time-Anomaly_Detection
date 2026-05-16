from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import base64

from forensics import perform_ela, extract_metadata, detect_copy_move
from local_validation import run_local_validation

app = FastAPI(title="Document Tampering and Fraud Detection API")

# Configure CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for demo purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisResult(BaseModel):
    file_name: str
    risk_score: float
    heatmap_image_b64: str
    anomalies: List[str]
    metadata: dict
    extracted_text: str
    validation_status: str
    validation_checks: List[str]
    ocr_confidence: float | None = None

@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def analyze_document(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not content_type.startswith('image/') and content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image or PDF.")

    file_bytes = await file.read()
    file_name = file.filename or "uploaded-document"
    
    # Track all anomalies across modules
    all_anomalies = []
    
    # 1. Document Ingestion & Metadata Checking
    metadata, meta_anomalies = extract_metadata(file_bytes)
    all_anomalies.extend(meta_anomalies)
    
    # 2. Forensic Analysis (ELA)
    heatmap_bytes, risk_score, ela_anomalies = perform_ela(file_bytes)
    all_anomalies.extend(ela_anomalies)
    
    # Convert heatmap to base64 for frontend display
    heatmap_b64 = ""
    if heatmap_bytes:
        heatmap_b64 = base64.b64encode(heatmap_bytes).decode('utf-8')
        
    # 2.5 Copy-Move Detection
    cm_risk_score, cm_anomalies = detect_copy_move(file_bytes)
    all_anomalies.extend(cm_anomalies)
    
    # 3. Local Document Validation
    validation_results, validation_anomalies = run_local_validation(file_bytes, file_name)
    all_anomalies.extend(validation_anomalies)
    
    # Synthesize Final Risk Score
    # Base risk score from ELA and Copy-Move
    final_risk_score = max(risk_score, cm_risk_score)
    if meta_anomalies:
        final_risk_score = min(100.0, final_risk_score + 20.0)
    if validation_anomalies:
        final_risk_score = min(100.0, final_risk_score + 30.0)

    return AnalysisResult(
        file_name=file_name,
        risk_score=final_risk_score,
        heatmap_image_b64=heatmap_b64,
        anomalies=all_anomalies,
        metadata=metadata,
        extracted_text=validation_results.get("extracted_text", ""),
        validation_status=validation_results.get("validation_status", ""),
        validation_checks=validation_results.get("validation_checks", []),
        ocr_confidence=validation_results.get("ocr_confidence"),
    )

@app.get("/health")
def health_check():
    return {"status": "healthy"}
