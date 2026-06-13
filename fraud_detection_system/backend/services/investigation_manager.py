import logging
import asyncio
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.database import Investigation, Document, Finding, Evidence
from services.event_logger import log_event
from layers.extraction.extraction_service import extraction_service
from layers.forensics.digital_forensics import digital_forensics
from layers.cross_document.cross_document_validator import cross_document_validator
from layers.scoring.trust_engine import trust_engine
from layers.ai.summary_generator import summary_generator
from core.database import SessionLocal

from layers.context.context_templates import get_rules_for_context
from layers.context.financial_validator import validate_bank_statement_math, validate_payslip_math
from layers.context.real_estate_signals import detect_real_estate_fraud_signals

logger = logging.getLogger(__name__)

class InvestigationManager:
    """
    Orchestrates the multi-step investigation pipeline asynchronously.
    """
    
    async def run_analysis(self, investigation_id: str):
        """
        The main entry point for the analysis pipeline.
        Runs as a background task.
        """
        db = SessionLocal()
        investigation = None
        try:
            investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
            if not investigation:
                logger.error(f"Investigation {investigation_id} not found")
                return

            # Reset previous results if any
            self._reset_investigation(db, investigation)
            
            # Start Pipeline
            await self._update_status(db, investigation, "PROCESSING", 0, "ANALYSIS_STARTED")
            
            # 1. Extraction, Classification & Forensics (Per Document)
            docs = investigation.documents
            total_docs = len(docs)
            extraction_success_count = 0
            
            if total_docs == 0:
                raise Exception("No documents uploaded for this investigation.")

            for idx, doc in enumerate(docs):
                success = await self._process_single_document(db, investigation, doc, idx, total_docs)
                if success:
                    extraction_success_count += 1
            
            if extraction_success_count == 0:
                raise Exception("Unable to extract text from uploaded documents. All documents failed extraction.")
            
            # 2. Context Validation
            await self._update_status(db, investigation, "PROCESSING", 60, "CONTEXT_VALIDATION")
            self._run_context_validation(db, investigation)
            
            # 3. Cross-Document Validation
            await self._update_status(db, investigation, "PROCESSING", 70, "CROSS_DOCUMENT_VALIDATION")
            cross_document_validator.validate_investigation(db, investigation_id)
            
            # 4. Trust Scoring
            await self._update_status(db, investigation, "PROCESSING", 80, "CALCULATING_TRUST_SCORE")
            self._calculate_final_scores(db, investigation)
            
            # 5. AI Summary
            await self._update_status(db, investigation, "PROCESSING", 90, "GENERATING_AI_SUMMARY")
            self._generate_ai_summary(db, investigation)
            
            # 6. Finalize
            await self._update_status(db, investigation, "COMPLETED", 100, "ANALYSIS_COMPLETED")
            log_event(db, investigation_id, "REPORT_READY", "The final investigation report is ready for review.")

        except Exception as e:
            logger.exception(f"Pipeline failed for investigation {investigation_id}: {e}")
            if investigation:
                investigation.status = "FAILED"
                investigation.current_stage = "ERROR"
                # Store message for GET /status
                investigation.ai_summary_json = {"error": str(e)}
                log_event(db, investigation_id, "PIPELINE_ERROR", str(e))
                db.commit()
        finally:
            db.close()

    async def _process_single_document(self, db: Session, investigation: Investigation, doc: Document, index: int, total: int) -> bool:
        """
        Handles the per-document layers. Returns True if extraction succeeded.
        """
        base_progress = 10
        doc_progress_share = 50 / total # Scale document processing to 50% of total bar
        
        current_progress = int(base_progress + (index * doc_progress_share))
        await self._update_status(db, investigation, "PROCESSING", current_progress, f"PROCESSING_DOCUMENT: {doc.filename}")
        
        try:
            # Read file bytes
            with open(doc.storage_path, "rb") as f:
                file_bytes = f.read()
                
            # A. Extraction Layer
            results = extraction_service.process_document(file_bytes, doc.filename, doc.file_type)
            
            doc.extracted_text = results.get("extracted_text")
            doc.classification = results.get("classification")
            doc.entities_json = results.get("entities")
            doc.metadata_json = {
                "raw_metadata": results.get("metadata"),
                "coordinates": results.get("coordinates")
            }
            db.commit()
            
            if not doc.extracted_text:
                return False

            # B. Forensics Layer (Single Doc)
            forensic_findings = digital_forensics.analyze(file_bytes, doc.filename, doc.file_type, results.get("metadata", {}))
            
            for ff in forensic_findings:
                finding = Finding(
                    investigation_id=investigation.id,
                    layer_source="FORENSIC",
                    name=ff["name"],
                    severity=ff["severity"],
                    description=ff["description"],
                    metadata_json=ff.get("evidence", [])
                )
                db.add(finding)
                log_event(db, investigation.id, "FINDING_DETECTED", f"Forensic flag: {ff['name']} on {doc.filename}")
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to process document {doc.filename}: {e}")
            return False

    def _run_context_validation(self, db: Session, investigation: Investigation):
        """
        Runs context-specific validation rules.
        """
        rules = get_rules_for_context(investigation.context)
        if not rules:
            return

        for doc in investigation.documents:
            if not doc.extracted_text:
                continue

            # Bank Statement Validation
            if doc.classification == "Bank Statement":
                results = validate_bank_statement_math(doc.extracted_text)
                if results.get("validation_results"):
                    for vr in results["validation_results"]:
                        finding = Finding(
                            investigation_id=investigation.id,
                            layer_source="CONTEXT",
                            name=vr["type"].replace("_", " ").title(),
                            severity=vr["severity"].upper(),
                            description=vr["description"]
                        )
                        db.add(finding)
            
            # Payslip Validation
            if doc.classification == "Payslip":
                results = validate_payslip_math(doc.extracted_text)
                if results.get("validation_results"):
                    for vr in results["validation_results"]:
                        finding = Finding(
                            investigation_id=investigation.id,
                            layer_source="CONTEXT",
                            name=vr["type"].replace("_", " ").title(),
                            severity=vr["severity"].upper(),
                            description=vr["description"]
                        )
                        db.add(finding)
            
            # Real Estate Signals
            if investigation.context.lower() in ["mortgage underwriting", "tenant screening"]:
                metadata = doc.metadata_json.get("raw_metadata", {}) if doc.metadata_json else {}
                with open(doc.storage_path, "rb") as f:
                    file_bytes = f.read()
                re_signals = detect_real_estate_fraud_signals(file_bytes, doc.extracted_text, metadata, doc.file_type)
                for res in re_signals:
                    finding = Finding(
                        investigation_id=investigation.id,
                        layer_source="CONTEXT",
                        name=res["name"],
                        severity=res["severity"].upper(),
                        description=res["summary"]
                    )
                    db.add(finding)
        
        db.commit()

    def _calculate_final_scores(self, db: Session, investigation: Investigation):
        """
        Wraps the Trust Engine.
        """
        findings = [
            {"layer_source": f.layer_source, "severity": f.severity, "name": f.name} 
            for f in investigation.findings
        ]
        
        # Aggregate metrics (placeholder for real OCR/Entity stats)
        metrics = {
            "ocr_quality": 95.0,
            "entity_success_rate": 90.0,
            "evidence_clarity": 85.0
        }
        
        # We assume Mortgage context for now or get from investigation.context
        # Context templates would define expected doc counts
        expected = 2 # Placeholder
        
        t, c, r = trust_engine.calculate_scores(findings, metrics, expected, len(investigation.documents))
        
        investigation.trust_score = t
        investigation.confidence_score = c
        investigation.recommendation = r
        db.commit()

    def _generate_ai_summary(self, db: Session, investigation: Investigation):
        """
        Wraps the AI Summary Generator.
        """
        # Prepare data for AI
        data = {
            "context": investigation.context,
            "trust_score": investigation.trust_score,
            "confidence_score": investigation.confidence_score,
            "recommendation": investigation.recommendation,
            "findings": [
                {"name": f.name, "severity": f.severity, "description": f.description}
                for f in investigation.findings
            ]
        }
        
        summary = summary_generator.generate_summary(data)
        investigation.ai_summary_json = summary
        db.commit()

    async def _update_status(self, db: Session, investigation: Investigation, status: str, progress: int, stage: str):
        investigation.status = status
        investigation.progress = progress
        investigation.current_stage = stage
        db.commit()
        log_event(db, investigation.id, stage, f"Pipeline moved to {stage} stage.")
        await asyncio.sleep(0.1) # Yield control

    def _reset_investigation(self, db: Session, investigation: Investigation):
        """
        Clears previous findings/evidence for a re-run.
        """
        db.query(Finding).filter(Finding.investigation_id == investigation.id).delete()
        # Events are kept as history, or cleared based on requirement.
        # For now we keep them but add a 'RESTARTED' event.
        log_event(db, investigation.id, "ANALYSIS_RESTARTED", "Investigation analysis has been restarted.")
        db.commit()

investigation_manager = InvestigationManager()
