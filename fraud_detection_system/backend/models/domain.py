from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

# --- Response Models for /api/v1/investigate endpoint ---

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    page: int

class AnomalyFeature(BaseModel):
    type: str = Field(..., description="The category of the anomaly (e.g., 'Suspicious Metadata', 'Mathematical Error')")
    description: str = Field(..., description="Detailed description of why this was flagged")
    risk_level: str = Field(..., description="Must be 'Critical', 'High', 'Medium', or 'Low'")
    bbox: Optional[BoundingBox] = Field(None, description="Coordinates to highlight the anomaly on the frontend")

class InvestigationResponse(BaseModel):
    filename: str
    fraud_probability_score: int = Field(..., description="0 to 100 score")
    status: str = Field(..., description="'TRUSTED', 'SUSPICIOUS', or 'TAMPERED'")
    anomalies: List[AnomalyFeature]
    ai_summary: Optional[dict] = Field(None, description="AI-generated summary of the analysis")


# --- CRUD Schemas for /api/v1/investigations endpoints ---

class InvestigationCreate(BaseModel):
    context: str = Field(..., description="Investigation context like 'loan_approval', 'kyc', etc.")
    title: Optional[str] = Field(None, description="Optional title for the investigation")

class DocumentSchema(BaseModel):
    id: str
    filename: str
    file_type: Optional[str] = None
    classification: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvestigationEventSchema(BaseModel):
    id: str
    investigation_id: str
    timestamp: Optional[datetime] = None
    event_type: str
    message: str
    metadata_json: Optional[Any] = None

    class Config:
        from_attributes = True

class FindingSchema(BaseModel):
    id: str
    layer_source: str
    name: str
    severity: str
    description: str
    metadata_json: Optional[Any] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvestigationSchema(BaseModel):
    id: str
    title: Optional[str] = None
    context: str
    status: str
    progress: int
    current_stage: str
    trust_score: Optional[float] = None
    confidence_score: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvestigationStatusSchema(BaseModel):
    status: str
    progress: int
    current_stage: str
    message: Optional[str] = None

class InvestigationFullSchema(InvestigationSchema):
    documents: List[DocumentSchema] = []
    findings: List[FindingSchema] = []
    events: List[InvestigationEventSchema] = []
    ai_summary_json: Optional[Any] = None

    class Config:
        from_attributes = True
