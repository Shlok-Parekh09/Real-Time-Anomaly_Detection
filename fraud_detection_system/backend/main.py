from __future__ import annotations

from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from forensics import (
    analyze_forensic_signals,
    calculate_risk_score,
    detect_file_type,
    extract_metadata,
    generate_cerebras_explanation,
)
from local_validation import run_local_validation


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
    ".xlsx",
    ".xlsm",
    ".xltx",
    ".xltm",
    ".xls",
    ".csv",
    ".tsv",
}


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


def _is_allowed_upload(file_name: str, content_type: str, file_bytes: bytes) -> bool:
    lower_name = (file_name or "").lower()
    has_allowed_extension = any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS)
    detected_type = detect_file_type(file_name, content_type, file_bytes)
    return has_allowed_extension or detected_type in {"pdf", "image", "excel"}


@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def analyze_document(file: UploadFile = File(...)):
    file_name = file.filename or "uploaded-document"
    content_type = file.content_type or ""
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not _is_allowed_upload(file_name, content_type, file_bytes):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Upload PDF, image, Excel workbook, CSV, or TSV files.",
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

    ai_explanation = generate_cerebras_explanation(
        file_name=file_name,
        risk_score=risk_score,
        trust_score=trust_score,
        signals=fraud_signals,
        recovered_version=recovered_version,
        validation_status=validation_results.get("validation_status", ""),
        extracted_text=validation_results.get("extracted_text", ""),
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


@app.get("/health")
def health_check():
    return {"status": "healthy", "features": ["pdf", "image", "excel", "xray", "cerebras"]}
