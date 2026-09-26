import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=True)
    context = Column(String, index=True)
    status = Column(String, default="PENDING")
    progress = Column(Integer, default=0)
    current_stage = Column(String, default="IDLE")
    trust_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    recommendation = Column(String, nullable=True)
    ai_summary_json = Column(JSON, nullable=True)
    is_baseline = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="investigation", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="investigation", cascade="all, delete-orphan")
    events = relationship("InvestigationEvent", back_populates="investigation", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="investigation", cascade="all, delete-orphan")

class InvestigationEvent(Base):
    __tablename__ = "investigation_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String)
    message = Column(String)
    metadata_json = Column(JSON, nullable=True)

    investigation = relationship("Investigation", back_populates="events")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"))
    filename = Column(String)
    file_type = Column(String)
    storage_path = Column(String)
    classification = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    entities_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="documents")
    evidence = relationship("Evidence", back_populates="document")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=generate_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"))
    layer_source = Column(String) # FORENSIC, CONTEXT, CROSS_DOC, KNN
    name = Column(String)
    severity = Column(String) # HIGH, MEDIUM, LOW
    description = Column(Text)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="findings")
    evidence_items = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=generate_uuid)
    finding_id = Column(String, ForeignKey("findings.id"))
    document_id = Column(String, ForeignKey("documents.id"))
    page_number = Column(Integer, nullable=True)
    coordinates = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    extracted_text = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    finding = relationship("Finding", back_populates="evidence_items")
    document = relationship("Document", back_populates="evidence")

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"))
    report_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="reports")
