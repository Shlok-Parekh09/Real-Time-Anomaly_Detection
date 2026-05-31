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
    extract_metadata,
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
    converted_to_pdf: bool = False
    pdf_data_base64: str | None = None


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
    
    has_allowed_extension = any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS)
    detected_type = detect_file_type(file_name, content_type, file_bytes)
    
    return has_allowed_extension and detected_type == "pdf"


@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def analyze_document(file: UploadFile = File(...), use_browser_ai: bool = False):
    """
    Analyze document for fraud.
    
    Returns a complete evidence-based fraud analysis from local parsers and
    forensic checks. No canned analysis or fixed fallback score is used.
    """
    file_name = file.filename or "uploaded-document"
    content_type = file.content_type or ""
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not _is_allowed_upload(file_name, content_type, file_bytes):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF documents are supported for real estate and banking forensic analysis.",
        )

    file_type = "pdf"

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

    risk_score = round(max(0.0, min(100.0, float(feature_summary.get("risk_score", calculate_risk_score(fraud_signals))))), 1)
    trust_score = round(max(0.0, 100.0 - risk_score), 1)
    anomalies = [signal["summary"] for signal in fraud_signals]

    ai_explanation = {
        "summary": feature_summary.get("ai_summary", f"Document analyzed with {len(fraud_signals)} fraud signals detected."),
        "likely_alteration": feature_summary.get("ai_alteration", "Analysis based on forensic signals and patterns."),
        "recommended_action": feature_summary.get("ai_recommendation", "Review fraud signals and make decision based on severity."),
        "limitations": feature_summary.get("ai_limitations", "Analysis is based on local forensic checks and available parsers."),
        "generated_by": feature_summary.get("analysis_method", "deterministic_local_forensics"),
    }

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
    )


@app.post("/api/v1/review-decision", response_model=ReviewDecisionResult)
async def submit_review_decision(
    decision: str = Form(...),
    file: UploadFile = File(...),
    analysis_json: str = Form(...),
):
    """
    Store the review decision (accepted/rejected) in the SQLite database.
    """
    if decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'accepted' or 'rejected'")

    file_bytes = await file.read()
    try:
        analysis = json.loads(analysis_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid analysis_json")

    result = store_review_document(
        decision=decision,
        file_name=file.filename or "unknown",
        content_type=file.content_type or "application/pdf",
        file_bytes=file_bytes,
        analysis=analysis,
    )

    if decision == "accepted":
        try:
            from rag_engine import add_document_to_knowledge_base
            text = analysis.get("extracted_text", "")
            if text:
                add_document_to_knowledge_base(text, result["file_sha256"])
        except Exception as e:
            print(f"[RAG] Failed to add document to knowledge base: {e}")

    return ReviewDecisionResult(
        status="success",
        decision=result["decision"],
        file_sha256=result["file_sha256"],
        stored_at=result["stored_at"],
    )


@app.post("/api/v1/highlighted-document")
async def get_highlighted_document(
    file: UploadFile = File(...),
    highlight_regions: str = Form("[]"),
):
    """
    Returns a highlighted version of the document.
    Only supports PDFs.
    """
    file_bytes = await file.read()
    file_name = file.filename or ""
    content_type = file.content_type or ""
    
    try:
        regions = json.loads(highlight_regions)
    except json.JSONDecodeError:
        regions = []

    if not _is_allowed_upload(file_name, content_type, file_bytes):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    from fastapi.responses import Response
    from pdf_highlighter import create_highlighted_pdf_preview
    
    # We only support PDFs now
    highlighted_bytes = create_highlighted_pdf_preview(file_bytes, regions)
    return Response(content=highlighted_bytes, media_type="application/pdf")
