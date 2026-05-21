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
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"}
EXCEL_CONTENT_TYPES = {
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.template",
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
    
    if detected_type in {"pdf", "word", "excel"}:
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
async def analyze_document(file: UploadFile = File(...), cerebras_api_key: str | None = Form(None)):
    file_name = file.filename or "uploaded-document"
    content_type = file.content_type or ""
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not _is_allowed_upload(file_name, content_type, file_bytes):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Upload PDF, Word, Excel, or image files.",
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

    risk_score = calculate_risk_score(fraud_signals)
    trust_score = round(max(0.0, 100.0 - risk_score), 1)
    anomalies = [signal["summary"] for signal in fraud_signals]

    ai_explanation = generate_openrouter_explanation(
        file_name=file_name,
        risk_score=risk_score,
        trust_score=trust_score,
        signals=fraud_signals,
        recovered_version=recovered_version,
        validation_status=validation_results.get("validation_status", ""),
        extracted_text=validation_results.get("extracted_text", ""),
        api_key=cerebras_api_key,
    )

    # Enrich per-signal descriptions via Cerebras when an API key is available
    fraud_signals = enrich_signal_descriptions(
        fraud_signals,
        file_name=file_name,
        api_key=cerebras_api_key,
    )

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
    return {"status": "healthy", "features": ["pdf", "image", "xray", "cerebras", "review_database"]}
