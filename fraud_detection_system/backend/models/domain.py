from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field

class InvestigationBase(BaseModel):
    context: str
    title: Optional[str] = None

class InvestigationCreate(InvestigationBase):
    pass

class EvidenceBase(BaseModel):
    document_id: str
    page_number: Optional[int] = None
    coordinates: Optional[Any] = None
    confidence: Optional[float] = None
    extracted_text: Optional[str] = None
    description: Optional[str] = None

class EvidenceSchema(EvidenceBase):
    id: str
    finding_id: str

    class Config:
        from_attributes = True

class FindingBase(BaseModel):
    layer_source: str
    name: str
    severity: str
    description: str
    metadata_json: Optional[Any] = None

class FindingSchema(FindingBase):
    id: str
    investigation_id: str
    evidence_items: List[EvidenceSchema] = []

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str
    file_type: str

class DocumentSchema(DocumentBase):
    id: str
    classification: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class InvestigationEventSchema(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    message: str
    metadata_json: Optional[Any] = None

    class Config:
        from_attributes = True

class InvestigationStatusSchema(BaseModel):
    status: str
    progress: int
    current_stage: str
    message: Optional[str] = None

class InvestigationSchema(InvestigationBase):
    id: str
    status: str
    progress: int
    current_stage: str
    trust_score: Optional[float] = None
    confidence_score: Optional[float] = None
    recommendation: Optional[str] = None
    ai_summary_json: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentSchema] = []

    class Config:
        from_attributes = True

class InvestigationFullSchema(InvestigationSchema):
    findings: List[FindingSchema] = []
    events: List[InvestigationEventSchema] = []
