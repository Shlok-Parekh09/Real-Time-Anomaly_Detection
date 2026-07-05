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
    
    async def process_document(self, file_path: str, filename: str):
        """
        Processes a single document for instant direct analysis (legacy API support).
        """
        import os
        from layers.forensics.digital_forensics import digital_forensics
        from layers.extraction.extraction_service import extraction_service
        from layers.context.financial_validator import validate_bank_statement_math, validate_payslip_math
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        ext = os.path.splitext(filename)[1].lower()
        content_type = "application/pdf" if ext == ".pdf" else "image/jpeg"
        
        # Extract metadata
        metadata = {}
        if ext == ".pdf":
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                metadata = doc.metadata or {}
                doc.close()
            except Exception as e_meta:
                logger.error(f"Failed to extract metadata for legacy process_document: {e_meta}")

        # Run digital forensics
        forensic_results = digital_forensics.analyze(file_bytes, filename, content_type, metadata)
        
        # Classify and extract text to check context math rules
        anomalies = []
        for fr in forensic_results:
            anomalies.append({
                "type": fr["name"],
                "severity": fr["severity"],
                "description": fr["description"]
            })
            
        try:
            extraction_results = extraction_service.process_document(file_bytes, filename, ext.replace(".", ""))
            extracted_text = extraction_results.get("extracted_text", "")
            classification = extraction_results.get("classification", "")
            
            if classification == "Bank Statement" and extracted_text:
                from layers.context.balance_validator import validate_running_balances
                math_anomalies = validate_running_balances(file_path)
                for anomaly in math_anomalies:
                    anomalies.append({
                        "type": anomaly.type,
                        "severity": anomaly.risk_level.upper(),
                        "description": anomaly.description
                    })
            elif classification == "Payslip" and extracted_text:
                math_res = validate_payslip_math(extracted_text)
                if math_res.get("validation_results"):
                    for vr in math_res["validation_results"]:
                        anomalies.append({
                            "type": vr["type"].replace("_", " ").title(),
                            "severity": vr["severity"].upper(),
                            "description": vr["description"]
                        })
        except Exception as e_ext:
            logger.error(f"Legacy process_document text/math analysis failed: {e_ext}")
            
        # Calculate a simple score
        score = 100.0
        if anomalies:
            score = max(0.0, 100.0 - (len(anomalies) * 15))
            
        class DirectAnalysisResult:
            def __init__(self, score, status, anomalies_list):
                self.fraud_probability_score = round(100.0 - score, 2)
                self.status = "LOW_RISK" if self.fraud_probability_score <= 40 else ("MEDIUM_RISK" if self.fraud_probability_score < 70 else "HIGH_RISK")
                self.anomalies = anomalies_list
                self.ai_summary = f"Direct analysis of document complete. Identified {len(anomalies_list)} potential anomaly/anomalies."
                
        return DirectAnalysisResult(score, "COMPLETED", anomalies)

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
            
            # Auto-detect context if set to "Automatic Detection"
            if investigation.context == "Automatic Detection":
                classifications = [d.classification for d in docs if d.classification]
                detected_context = "Loan Approval" # Default fallback
                
                if any(c in ["Mortgage Statement", "Property Deed", "Title Deed"] for c in classifications):
                    detected_context = "Mortgage Underwriting"
                elif any(c in ["ID Card", "Passport", "Driver's License", "Utility Bill"] for c in classifications):
                    detected_context = "KYC / Onboarding"
                elif any("insurance" in str(c).lower() for c in classifications):
                    detected_context = "Insurance Claims"
                elif any(c in ["Rental Agreement", "Lease", "Tenancy Agreement"] for c in classifications):
                    detected_context = "Tenant Screening"
                elif any(c in ["Audit Report", "Financial Statement", "Balance Sheet"] for c in classifications):
                    detected_context = "Internal Audit"
                elif any(c in ["Bank Statement", "Payslip"] for c in classifications):
                    detected_context = "Loan Approval"
                    
                investigation.context = detected_context
                if investigation.title == "Investigation: Automatic Detection":
                    investigation.title = f"Investigation: {detected_context}"
                
                db.commit()
                log_event(db, investigation_id, "CONTEXT_AUTO_DETECTED", f"Automatically detected case context: {detected_context}")
            
            # 2. Reconcile entities cross-document & context validation
            await self._update_status(db, investigation, "PROCESSING", 60, "Context Validation")
            self._reconcile_cross_document_entities(db, investigation)
            self._run_context_validation(db, investigation)
            
            # 3. Cross-Document Validation
            from core.settings_store import settings_store
            if settings_store.get("enable_cross_doc_matching", True):
                await self._update_status(db, investigation, "PROCESSING", 70, "Cross-document Matching")
                cross_document_validator.validate_investigation(db, investigation_id)
            else:
                logger.info("Cross-document matching is disabled by configuration.")
            
            # 4. Trust Scoring
            await self._update_status(db, investigation, "PROCESSING", 78, "Reference Comparison")
            await self._update_status(db, investigation, "PROCESSING", 84, "Rule Engine")
            self._calculate_final_scores(db, investigation)
            
            # 5. AI Summary
            await self._update_status(db, investigation, "PROCESSING", 92, "AI Investigation")
            self._generate_ai_summary(db, investigation)
            
            # 6. Finalize
            await self._update_status(db, investigation, "PROCESSING", 98, "Generating Report")
            await self._update_status(db, investigation, "COMPLETED", 100, "Finalizing Investigation")
            log_event(db, investigation_id, "REPORT_READY", "The final investigation report is ready for review.")

            # Automatic Baseline Learning
            if settings_store.get("auto_baseline_learning", True):
                min_trust = float(settings_store.get("min_trust_threshold", 85.0))
                if investigation.trust_score is not None and investigation.trust_score >= min_trust:
                    try:
                        from layers.scoring.similarity_engine import similarity_engine
                        from trusted_repository.repository_manager import repository_manager
                        investigation.is_baseline = True
                        db.commit()
                        
                        features = similarity_engine.generate_feature_vector(db, investigation)
                        repository_manager.add_entry(
                            features=features,
                            metadata={
                                "investigation_id": investigation.id,
                                "title": investigation.title or f"Investigation: {investigation.context}",
                                "context": investigation.context,
                                "approved_at": investigation.updated_at.isoformat() if investigation.updated_at else None,
                                "document_count": len(investigation.documents),
                            }
                        )
                        log_event(db, investigation_id, "AUTO_BASELINE_PROMOTED", "Case automatically registered to the Reference Database based on high trust score.")
                        logger.info(f"Investigation {investigation_id} automatically promoted to baseline reference library.")
                    except Exception as ex_baseline:
                        logger.error(f"Failed to auto-promote investigation {investigation_id} to baseline: {ex_baseline}")

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
        
        def status_callback(stage_name: str, sub_percent: float):
            progress_val = int(base_progress + (index * doc_progress_share) + (sub_percent * doc_progress_share))
            investigation.status = "PROCESSING"
            investigation.progress = min(99, max(0, progress_val))
            investigation.current_stage = f"{stage_name}: {doc.filename}"
            db.commit()

        status_callback("Preparing OCR Pipeline", 0.0)
        
        try:
            # Read file bytes
            with open(doc.storage_path, "rb") as f:
                file_bytes = f.read()
                
            # A. Extraction Layer
            results = extraction_service.process_document(file_bytes, doc.filename, doc.file_type, status_callback=status_callback)
            
            doc.extracted_text = results.get("extracted_text")
            doc.classification = results.get("classification")
            doc.entities_json = results.get("entities")
            
            # Save converted PDF bytes back to storage if file type changed
            if results.get("pdf_bytes"):
                try:
                    with open(doc.storage_path, "wb") as f:
                        f.write(results["pdf_bytes"])
                    doc.file_type = "pdf"
                except Exception as e:
                    logger.error(f"Failed to overwrite storage path with PDF bytes for {doc.filename}: {e}")
            
            doc.metadata_json = {
                "raw_metadata": results.get("metadata"),
                "coordinates": results.get("coordinates"),
                "ocr_confidence": results.get("ocr_confidence", 100.0),
                "is_scanned": results.get("is_scanned", False)
            }
            db.commit()
            
            if not doc.extracted_text:
                return False

            # B. Forensics Layer (Single Doc)
            from core.settings_store import settings_store
            if settings_store.get("enable_metadata_analysis", True):
                forensics_metadata = results.get("metadata", {})
                if isinstance(forensics_metadata, dict):
                    forensics_metadata = forensics_metadata.copy()
                    forensics_metadata["extracted_text"] = results.get("extracted_text", "")
                else:
                    forensics_metadata = {"extracted_text": results.get("extracted_text", "")}
                    
                forensic_findings = digital_forensics.analyze(file_bytes, doc.filename, doc.file_type, forensics_metadata)
                
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
            else:
                logger.info("Metadata analysis is disabled by configuration.")
            
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
                from layers.context.balance_validator import validate_running_balances
                anomalies = validate_running_balances(doc.storage_path)
                for anomaly in anomalies:
                    finding = Finding(
                        investigation_id=investigation.id,
                        layer_source="CONTEXT",
                        name=anomaly.type,
                        severity=anomaly.risk_level.upper(),
                        description=anomaly.description
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
        Wraps the Trust Engine and calculates OCR, entity, and evidence metrics dynamically.
        """
        findings = [
            {"layer_source": f.layer_source, "severity": f.severity, "name": f.name} 
            for f in investigation.findings
        ]
        
        docs = investigation.documents
        total_docs = len(docs)
        
        # 1. Dynamic OCR Quality
        ocr_scores = []
        for doc in docs:
            if not doc.extracted_text:
                ocr_scores.append(0.0)
            else:
                meta = doc.metadata_json or {}
                if meta.get("is_scanned", False):
                    ocr_scores.append(meta.get("ocr_confidence", 100.0))
                else:
                    ocr_scores.append(100.0)
        avg_ocr_quality = sum(ocr_scores) / total_docs if total_docs > 0 else 100.0

        # 2. Dynamic Entity Success Rate
        entity_success_rates = []
        for doc in docs:
            if not doc.extracted_text:
                entity_success_rates.append(0.0)
                continue
                
            entities = doc.entities_json or {}
            cls = doc.classification
            
            # Map expected entities per classification type
            expected_keys = ["name"]
            if cls == "PAN":
                expected_keys = ["name", "dob", "pan"]
            elif cls == "Aadhaar":
                expected_keys = ["name", "dob", "aadhaar"]
            elif cls == "Payslip":
                expected_keys = ["name", "salary", "employer"]
            elif cls == "Property Record":
                expected_keys = ["property_owner", "property_id"]
            elif cls == "Bank Statement":
                expected_keys = ["name", "account_number"]
            elif cls in ["Utility Bill", "Lease Agreement"]:
                expected_keys = ["name", "address"]
                
            found_count = sum(1 for k in expected_keys if entities.get(k) is not None)
            success_rate = (found_count / len(expected_keys)) * 100.0
            entity_success_rates.append(success_rate)
            
        avg_entity_success = sum(entity_success_rates) / total_docs if total_docs > 0 else 100.0

        # 3. Dynamic Evidence Quality
        evidence_confs = []
        for f in investigation.findings:
            for ev in f.evidence_items:
                if ev.confidence is not None:
                    evidence_confs.append(ev.confidence * 100.0)
                    
        avg_evidence_clarity = sum(evidence_confs) / len(evidence_confs) if evidence_confs else 100.0

        # Flag poor image quality if any scanned doc has OCR confidence below 60%
        has_poor_ocr = any(
            doc.metadata_json and 
            doc.metadata_json.get("is_scanned") and 
            doc.metadata_json.get("ocr_confidence", 100.0) < 60.0 
            for doc in docs
        )

        metrics = {
            "ocr_quality": avg_ocr_quality,
            "entity_success_rate": avg_entity_success,
            "evidence_clarity": avg_evidence_clarity,
            "poor_image_quality": has_poor_ocr
        }
        
        # Determine expected document counts based on context
        expected = 2
        ctx_lower = investigation.context.lower()
        if "underwriting" in ctx_lower or "mortgage" in ctx_lower or "loan" in ctx_lower:
            expected = 3
        elif "screening" in ctx_lower or "kyc" in ctx_lower:
            expected = 2
            
        t, c, r = trust_engine.calculate_scores(findings, metrics, expected, total_docs)
        
        investigation.trust_score = t
        investigation.confidence_score = None
        investigation.recommendation = r
        db.commit()

    def _build_evidence_graph(self, db: Session, investigation: Investigation) -> Dict[str, Any]:
        """
        Creates a structured relationship graph mapping:
        Applicant -> Documents -> Entities -> Evidence -> Findings -> Recommendation
        """
        nodes = []
        edges = []
        
        # 1. Applicant node
        applicant_id = "applicant-1"
        # Try to find applicant name from documents
        applicant_name = "Unknown Applicant"
        for doc in investigation.documents:
            if doc.entities_json and doc.entities_json.get("name"):
                applicant_name = doc.entities_json["name"]
                break
                
        nodes.append({
            "id": applicant_id,
            "type": "Applicant",
            "label": applicant_name
        })
        
        # 2. Documents & Entities
        for doc in investigation.documents:
            doc_node_id = f"doc-{doc.id}"
            nodes.append({
                "id": doc_node_id,
                "type": "Document",
                "label": doc.filename,
                "classification": doc.classification or "Unknown"
            })
            # Edge: Applicant -> Document
            edges.append({
                "source": applicant_id,
                "target": doc_node_id,
                "relation": "submitted"
            })
            
            # Entities extracted from doc
            entities = doc.entities_json or {}
            for key, val in entities.items():
                if val:
                    ent_node_id = f"ent-{doc.id}-{key}"
                    nodes.append({
                        "id": ent_node_id,
                        "type": "Entity",
                        "label": f"{key}: {val}"
                    })
                    # Edge: Document -> Entity
                    edges.append({
                        "source": doc_node_id,
                        "target": ent_node_id,
                        "relation": "contains"
                    })
                    
        # 3. Findings & Evidence
        for idx, f in enumerate(investigation.findings):
            finding_node_id = f"finding-{f.id}"
            nodes.append({
                "id": finding_node_id,
                "type": "Finding",
                "label": f.name,
                "severity": f.severity,
                "layer": f.layer_source
            })
            
            # Edges from Evidence to Findings
            for ev in f.evidence_items:
                ev_node_id = f"ev-{ev.id}"
                nodes.append({
                    "id": ev_node_id,
                    "type": "Evidence",
                    "label": ev.description or "Tampering Indicator",
                    "observation": ev.description
                })
                # Edge: Document -> Evidence
                edges.append({
                    "source": f"doc-{ev.document_id}",
                    "target": ev_node_id,
                    "relation": "contains_evidence"
                })
                # Edge: Evidence -> Finding
                edges.append({
                    "source": ev_node_id,
                    "target": finding_node_id,
                    "relation": "supports"
                })
                
        # 4. Recommendation node
        rec_node_id = "rec-1"
        nodes.append({
            "id": rec_node_id,
            "type": "Recommendation",
            "label": investigation.recommendation or "MANUAL_REVIEW"
        })
        
        # Edges from Findings to Recommendation
        for f in investigation.findings:
            edges.append({
                "source": f"finding-{f.id}",
                "target": rec_node_id,
                "relation": "leads_to"
            })
            
        return {"nodes": nodes, "edges": edges}

    def _generate_ai_summary(self, db: Session, investigation: Investigation):
        """
        Wraps the AI Summary Generator. Runs Dataset Similarity & builds Evidence Graph before calling LLM.
        """
        from layers.scoring.similarity_engine import similarity_engine
        
        # 1. Run similarity check
        try:
            similarity_data = similarity_engine.search_similar_cases(db, investigation)
        except Exception as e:
            logger.error(f"Failed to calculate similarity during pipeline: {e}")
            similarity_data = {
                "similarity_score": 0.0,
                "explanation": f"Failed to compute similarity: {str(e)}",
                "top_similar_genuine": [],
                "top_similar_fraud": []
            }
            
        # 2. Build Evidence Graph
        evidence_graph = self._build_evidence_graph(db, investigation)
        
        # Compile all structured data to pass to LLM
        data = {
            "context": investigation.context,
            "trust_score": investigation.trust_score,
            "recommendation": investigation.recommendation,
            "findings": [
                {
                    "id": f.id,
                    "name": f.name,
                    "severity": f.severity,
                    "description": f.description,
                    "layer_source": f.layer_source,
                    "evidence": [
                        {
                            "document": e.document.filename,
                            "page": e.page_number,
                            "text": e.extracted_text,
                            "description": e.description
                        } for e in f.evidence_items
                    ]
                }
                for f in investigation.findings
            ],
            "documents": [
                {
                    "filename": d.filename,
                    "classification": d.classification,
                    "ocr_confidence": d.metadata_json.get("ocr_confidence", 100.0) if d.metadata_json else 100.0,
                    "metadata": d.metadata_json.get("raw_metadata", {}) if d.metadata_json else {}
                } for d in investigation.documents
            ],
            "dataset_similarity": similarity_data,
            "evidence_graph": evidence_graph,
            "timeline": [
                {"timestamp": ev.timestamp.isoformat(), "message": ev.message}
                for ev in investigation.events
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

    def _reconcile_cross_document_entities(self, db: Session, investigation: Investigation):
        """
        Reconciles names and identity fields across all documents in the investigation.
        If Doc A has a clean fully-qualified name (e.g. 'SHLOK PAREKH') and Doc B has a slightly
        noisy/partial name (e.g. 'SHLOK PARE') that is highly similar (similarity > 85%), 
        we reconcile Doc B's name to the more complete Doc A name to fix partial extractions.
        """
        from layers.cross_document.normalizer import normalizer
        docs = investigation.documents
        if len(docs) < 2:
            return
            
        # Find the best validated name across all documents
        best_name = None
        for doc in docs:
            name = doc.entities_json.get("name") if doc.entities_json else None
            if name and name != "-":
                if not best_name or len(name) > len(best_name):
                    best_name = name
                    
        if best_name:
            # Check other documents and reconcile if they have a highly similar but shorter/noisy name
            for doc in docs:
                name = doc.entities_json.get("name") if doc.entities_json else None
                if name and name != "-" and name != best_name:
                    norm1 = normalizer.normalize_name(name)
                    norm2 = normalizer.normalize_name(best_name)
                    sim = normalizer.calculate_similarity(norm1, norm2)
                    if sim < 0.92:
                        sim = max(sim, normalizer.handle_abbreviation(name, best_name), normalizer.handle_abbreviation(best_name, name))
                        
                    # If they are very similar (e.g. 85%), reconcile to the best name!
                    if sim >= 0.85:
                        entities = doc.entities_json.copy()
                        entities["name"] = best_name
                        doc.entities_json = entities
                        
            db.commit()

investigation_manager = InvestigationManager()
