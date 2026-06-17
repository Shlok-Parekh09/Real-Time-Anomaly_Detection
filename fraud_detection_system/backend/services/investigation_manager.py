"""
Investigation Manager
Orchestrates the complete forensic analysis pipeline for uploaded documents.
Integrates all layers:
  - PDF Metadata Forensics
  - PDF Structure Analysis (%%EOF, /Prev pointers)
  - Font Consistency Analysis
  - Digital Signature Validation
  - Financial/Mathematical Validation (Benford's Law, round numbers)
  - Running Balance Verification
  - Date Validation
  - Image Pixel Forensics (ELA, compression noise, copy-paste)
  - AI Summary Generation (Ollama LLM / template fallback)
"""

import asyncio
import os
import logging
from typing import List

from models.domain import InvestigationResponse, AnomalyFeature

# Forensics layers
from layers.forensics.digital_forensics import validate_metadata
from layers.forensics.pdf_analyzer import pdf_analyzer
from layers.forensics.font_forensics import analyze_font_consistency
from layers.forensics.signature_validator import validate_digital_signatures
from layers.forensics.image_forensics import run_image_forensics

# Context/content validation layers
from layers.context.financial_validator import run_financial_analysis
from layers.context.date_validator import validate_dates
from layers.context.balance_validator import validate_running_balances

# Scoring
from layers.scoring.trust_engine import calculate_trust_score, calculate_confidence_score, get_recommendation

# AI summary
from layers.ai.summary_generator import summary_generator

logger = logging.getLogger(__name__)


class InvestigationManager:
    """
    Orchestrates the asynchronous execution of all forensic layers.
    Runs each layer independently so one failure doesn't block others.
    """

    async def process_document(self, file_path: str, filename: str) -> InvestigationResponse:
        anomalies: List[AnomalyFeature] = []
        is_pdf = file_path.lower().endswith('.pdf')
        is_image = file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))
        extracted_text = ""

        logger.info(f"[PIPELINE] Starting analysis of '{filename}' (PDF={is_pdf}, Image={is_image})")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 1: PDF Metadata Forensics
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if is_pdf:
            try:
                meta_anomalies = validate_metadata(file_path)
                anomalies.extend(meta_anomalies)
                logger.info(f"[PIPELINE] Metadata check: {len(meta_anomalies)} anomalies")
            except Exception as e:
                logger.error(f"[PIPELINE] Metadata check failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 2: PDF Structure Analysis
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if is_pdf:
            try:
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()
                
                import fitz
                doc = fitz.open(file_path)
                metadata = doc.metadata or {}
                # Extract text for use by other layers
                for page in doc:
                    extracted_text += page.get_text()
                doc.close()

                struct_findings = pdf_analyzer.analyze_structure(pdf_bytes, metadata)
                for finding in struct_findings:
                    anomalies.append(AnomalyFeature(
                        type=finding["name"],
                        description=finding["description"],
                        risk_level="High" if finding["severity"] == "HIGH" else "Medium"
                    ))
                logger.info(f"[PIPELINE] Structure check: {len(struct_findings)} anomalies")
            except Exception as e:
                logger.error(f"[PIPELINE] Structure check failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 3: Font Consistency Analysis
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if is_pdf:
            try:
                font_anomalies = analyze_font_consistency(file_path)
                anomalies.extend(font_anomalies)
                logger.info(f"[PIPELINE] Font check: {len(font_anomalies)} anomalies")
            except Exception as e:
                logger.error(f"[PIPELINE] Font check failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 4: Digital Signature Validation
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if is_pdf:
            try:
                sig_anomalies = validate_digital_signatures(file_path)
                anomalies.extend(sig_anomalies)
                logger.info(f"[PIPELINE] Signature check: {len(sig_anomalies)} anomalies")
            except Exception as e:
                logger.error(f"[PIPELINE] Signature check failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 5: Financial/Mathematical Validation
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if is_pdf:
            try:
                fin_anomalies = run_financial_analysis(file_path)
                anomalies.extend(fin_anomalies)
                logger.info(f"[PIPELINE] Financial check: {len(fin_anomalies)} anomalies")
            except Exception as e:
                logger.error(f"[PIPELINE] Financial check failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 6: Running Balance Verification
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if is_pdf:
            try:
                balance_anomalies = validate_running_balances(file_path)
                anomalies.extend(balance_anomalies)
                logger.info(f"[PIPELINE] Balance check: {len(balance_anomalies)} anomalies")
            except Exception as e:
                logger.error(f"[PIPELINE] Balance check failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 7: Date Validation
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if extracted_text:
            try:
                date_anomalies = validate_dates(extracted_text)
                anomalies.extend(date_anomalies)
                logger.info(f"[PIPELINE] Date check: {len(date_anomalies)} anomalies")
            except Exception as e:
                logger.error(f"[PIPELINE] Date check failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LAYER 8: Image/Pixel Forensics (for both images and PDFs)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            image_anomalies = run_image_forensics(file_path)
            anomalies.extend(image_anomalies)
            logger.info(f"[PIPELINE] Image forensics: {len(image_anomalies)} anomalies")
        except Exception as e:
            logger.error(f"[PIPELINE] Image forensics failed: {e}")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # SCORING ENGINE
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        fraud_score, status = calculate_trust_score(anomalies)
        confidence = calculate_confidence_score(anomalies, extracted_text)
        recommendation = get_recommendation(fraud_score, confidence)

        logger.info(
            f"[PIPELINE] Scoring complete: fraud_score={fraud_score}, "
            f"status={status}, confidence={confidence}, recommendation={recommendation}"
        )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # AI SUMMARY GENERATION (Ollama LLM / fallback)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            summary_data = {
                "filename": filename,
                "fraud_probability_score": fraud_score,
                "status": status,
                "confidence": confidence,
                "recommendation": recommendation,
                "anomalies": [
                    {
                        "type": a.type,
                        "description": a.description,
                        "risk_level": a.risk_level
                    }
                    for a in anomalies
                ]
            }
            ai_summary = summary_generator.generate_summary(summary_data)
            logger.info("[PIPELINE] AI summary generated successfully")
        except Exception as e:
            logger.error(f"[PIPELINE] AI summary generation failed: {e}")
            ai_summary = {
                "executive_summary": f"Analysis complete. {len(anomalies)} anomalies detected. Score: {fraud_score}/100.",
                "hindi_summary": f"विश्लेषण पूर्ण। {len(anomalies)} विसंगतियाँ पाई गईं। स्कोर: {fraud_score}/100।",
                "reviewer_notes": "AI summary generation encountered an error. Please review anomalies manually."
            }

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # BUILD RESPONSE
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        return InvestigationResponse(
            filename=filename,
            fraud_probability_score=fraud_score,
            status=status,
            anomalies=anomalies,
            ai_summary=ai_summary
        )

    async def run_analysis(self, investigation_id: str):
        """
        Background analysis for the CRUD-based investigation workflow.
        Used by routes.py for async processing.
        """
        from core.database import SessionLocal
        from models.database import Investigation, Document

        db = SessionLocal()
        try:
            investigation = db.query(Investigation).filter(
                Investigation.id == investigation_id
            ).first()

            if not investigation:
                return

            investigation.status = "PROCESSING"
            investigation.current_stage = "ANALYSIS"
            investigation.progress = 10
            db.commit()

            # Process each document
            all_anomalies = []
            docs = investigation.documents

            for i, doc in enumerate(docs):
                progress = 10 + int((i / max(len(docs), 1)) * 70)
                investigation.progress = progress
                investigation.current_stage = f"ANALYZING_{doc.filename}"
                db.commit()

                try:
                    result = await self.process_document(doc.storage_path, doc.filename)
                    all_anomalies.extend(result.anomalies)
                except Exception as e:
                    logger.error(f"[PIPELINE] Error processing {doc.filename}: {e}")

            # Calculate final scores
            fraud_score, status = calculate_trust_score(all_anomalies)
            confidence = calculate_confidence_score(all_anomalies)
            recommendation = get_recommendation(fraud_score, confidence)

            investigation.trust_score = 100 - fraud_score  # Trust is inverse of fraud
            investigation.confidence_score = confidence
            investigation.recommendation = recommendation
            investigation.status = "COMPLETED"
            investigation.progress = 100
            investigation.current_stage = "DONE"
            
            # Generate AI summary
            try:
                summary_data = {
                    "filename": "investigation",
                    "fraud_probability_score": fraud_score,
                    "status": status,
                    "anomalies": [{"type": a.type, "description": a.description, "risk_level": a.risk_level} for a in all_anomalies]
                }
                investigation.ai_summary_json = summary_generator.generate_summary(summary_data)
            except Exception:
                investigation.ai_summary_json = {"error": "Summary generation failed"}

            db.commit()

        except Exception as e:
            investigation.status = "FAILED"
            investigation.ai_summary_json = {"error": str(e)}
            db.commit()
        finally:
            db.close()


# Module-level singleton for routes.py import
investigation_manager = InvestigationManager()
