from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from forensics import (
    analyze_forensic_signals,
    calculate_risk_score,
    detect_file_type,
    enrich_signal_descriptions,
    extract_metadata,
    generate_openrouter_explanation,
)
from local_validation import run_local_validation
from review_store import init_review_database, store_review_document


app = FastAPI(title="Document Tampering and Fraud Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class FraudSignal(BaseModel):
    id: str
    name: str
    severity: str
    summary: str
    description: str
    evidence: list[str]
    confidence: float
    recovered_version_available: bool = False


class RecoveredChange(BaseModel):
    field: str
    previous_value: str
    current_value: str
    type: str


class RecoveredSection(BaseModel):
    title: str
    items: list[str]


class RecoveredVersion(BaseModel):
    available: bool
    title: str
    summary: str
    method: str
    preview_text: str
    sections: list[RecoveredSection]
    changes: list[RecoveredChange]
    confidence: float


class AiExplanation(BaseModel):
    summary: str
    likely_alteration: str
    recommended_action: str
    limitations: str
    generated_by: str


class AnalysisResult(BaseModel):
    file_name: str
    file_type: str
    risk_score: float
    trust_score: float
    anomalies: list[str]
    fraud_signals: list[FraudSignal]
    recovered_version: RecoveredVersion
    ai_explanation: AiExplanation
    metadata: dict[str, Any]
    feature_summary: dict[str, Any]
    extracted_text: str
    validation_status: str
    validation_checks: list[str]
    ocr_confidence: float | None = None
    converted_to_pdf: bool = False  # Indicates if Word was converted to PDF
    pdf_data_base64: str | None = None  # Base64 encoded PDF for Word documents


class ReviewDecisionResult(BaseModel):
    status: str
    decision: str
    file_sha256: str
    stored_at: str


@app.on_event("startup")
def startup() -> None:
    init_review_database()


def _is_allowed_upload(file_name: str, content_type: str, file_bytes: bytes) -> bool:
    lower_name = (file_name or "").lower()
    lower_type = (content_type or "").lower()
    
    has_allowed_extension = any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS)
    detected_type = detect_file_type(file_name, content_type, file_bytes)
    
    # Only allow PDF and images (NO Word/Excel)
    if detected_type == "pdf":
        return True
    
    return has_allowed_extension and detected_type == "image" and _looks_like_image(file_bytes, lower_type)


def _is_ooxml_workbook(file_bytes: bytes) -> bool:
    if not file_bytes.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            return "xl/workbook.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def _looks_like_image(file_bytes: bytes, content_type: str) -> bool:
    if content_type.startswith("image/"):
        return True
    return (
        file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        or file_bytes.startswith(b"\xff\xd8\xff")
        or file_bytes.startswith(b"BM")
        or file_bytes.startswith((b"II*\x00", b"MM\x00*"))
        or (file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP")
    )


@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def analyze_document(file: UploadFile = File(...), use_browser_ai: bool = False):
    """
    Analyze document for fraud.
    
    If use_browser_ai=true, returns document context for browser-based AI analysis (Puter.js).
    Otherwise, uses local Ollama (if available) or fallback.
    """
    file_name = file.filename or "uploaded-document"
    content_type = file.content_type or ""
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not _is_allowed_upload(file_name, content_type, file_bytes):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and image files are supported. Word and Excel files are not accepted.",
        )

    file_type = detect_file_type(file_name, content_type, file_bytes)

    metadata, metadata_anomalies = extract_metadata(file_bytes, file_name, content_type)
    validation_results, validation_anomalies = run_local_validation(file_bytes, file_name, content_type)

    fraud_signals, recovered_version, feature_summary = analyze_forensic_signals(
        file_bytes,
        file_name,
        content_type,
        metadata,
        metadata_anomalies,
        validation_anomalies,
    )

    # Extract risk/trust scores from Gemma4 analysis (if available)
    risk_score = feature_summary.get("risk_score", calculate_risk_score(fraud_signals))
    trust_score = round(max(0.0, 100.0 - risk_score), 1)
    anomalies = [signal["summary"] for signal in fraud_signals]

    # Extract AI explanation from Gemma4 analysis (if available)
    # Gemma4 includes ai_explanation in its response
    ai_explanation = {
        "summary": feature_summary.get("ai_summary", f"Document analyzed with {len(fraud_signals)} fraud signals detected."),
        "likely_alteration": feature_summary.get("ai_alteration", "Analysis based on forensic signals and patterns."),
        "recommended_action": feature_summary.get("ai_recommendation", "Review fraud signals and make decision based on severity."),
        "limitations": "Analysis performed using Gemma4 AI or fallback methods.",
        "generated_by": feature_summary.get("analysis_method", "gemma4_complete"),
    }

    # Signals already have descriptions from Gemma4
    # No additional enrichment needed

    return AnalysisResult(
        file_name=file_name,
        file_type=file_type,
        risk_score=risk_score,
        trust_score=trust_score,
        anomalies=anomalies,
        fraud_signals=fraud_signals,
        recovered_version=recovered_version,
        ai_explanation=ai_explanation,
        metadata=metadata,
        feature_summary=feature_summary,
        extracted_text=validation_results.get("extracted_text", ""),
        validation_status=validation_results.get("validation_status", ""),
        validation_checks=validation_results.get("validation_checks", []),
        ocr_confidence=validation_results.get("ocr_confidence"),
        converted_to_pdf=False,
        pdf_data_base64=None,
    )


@app.post("/api/v1/review-decision", response_model=ReviewDecisionResult)
async def save_review_decision(
    decision: str = Form(...),
    analysis_json: str = Form(...),
    file: UploadFile = File(...),
):
    normalized_decision = decision.strip().lower()
    if normalized_decision not in {"accepted", "rejected"}:
        raise HTTPException(status_code=400, detail="Decision must be accepted or rejected.")

    file_name = file.filename or "uploaded-document"
    content_type = file.content_type or ""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        analysis = json.loads(analysis_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid analysis payload: {exc}") from exc

    stored = store_review_document(
        decision=normalized_decision,
        file_name=file_name,
        content_type=content_type,
        file_bytes=file_bytes,
        analysis=analysis,
    )
    return ReviewDecisionResult(status="stored", **stored)


@app.get("/health")
def health_check():
    return {"status": "healthy", "features": ["pdf", "image", "xray", "opencv", "pymupdf", "financial_validation", "puter_browser_ai"]}


@app.post("/api/v1/extract-context")
async def extract_document_context(file: UploadFile = File(...)):
    """
    Extract document context for browser-based AI analysis (Puter.js).
    Returns metadata and text without AI analysis.
    """
    file_name = file.filename or "uploaded-document"
    content_type = file.content_type or ""
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not _is_allowed_upload(file_name, content_type, file_bytes):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and image files are supported.",
        )

    file_type = detect_file_type(file_name, content_type, file_bytes)
    metadata, metadata_anomalies = extract_metadata(file_bytes, file_name, content_type)
    validation_results, validation_anomalies = run_local_validation(file_bytes, file_name, content_type)

    # Return context for browser AI
    return {
        "file_name": file_name,
        "file_type": file_type,
        "metadata": metadata,
        "forensic_data": {
            "metadata_anomalies": metadata_anomalies,
            "validation_anomalies": validation_anomalies,
            "text_confidence": validation_results.get("confidence_score"),
        },
        "text_sample": validation_results.get("extracted_text", "")[:1000],
        "full_text": validation_results.get("extracted_text", ""),
    }


@app.post("/api/v1/highlighted-document")
async def get_highlighted_document(
    file: UploadFile = File(...),
    highlight_regions: str = Form(...),
):
    """
    Return a highlighted version of the document with colored highlights.
    """
    file_name = file.filename or "uploaded-document"
    content_type = file.content_type or ""
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Parse highlight regions
    try:
        regions = json.loads(highlight_regions)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid highlight_regions JSON: {exc}") from exc

    file_type = detect_file_type(file_name, content_type, file_bytes)

    # Add highlights based on file type
    if file_type == "pdf":
        try:
            from pdf_highlighter import create_highlighted_pdf_preview
            highlighted_bytes = create_highlighted_pdf_preview(file_bytes, regions)
            media_type = "application/pdf"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to highlight PDF: {e}") from e
    
    elif file_type == "image":
        try:
            from image_highlighter import create_highlighted_image_preview
            highlighted_bytes = create_highlighted_image_preview(file_bytes, regions)
            media_type = "image/png"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to highlight image: {e}") from e
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type for highlighting")

    # Return highlighted document
    from fastapi.responses import Response
    return Response(content=highlighted_bytes, media_type=media_type)
