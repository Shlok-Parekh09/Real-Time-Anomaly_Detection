import os
import json
import logging
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from models.database import Investigation, Finding, Document

logger = logging.getLogger(__name__)

# Weight Configuration for Forensic Feature Similarity
FEATURE_WEIGHTS = {
    "trust_score": 0.40,
    "ocr_confidence": 0.10,
    "metadata_score": 0.15,
    "revision_count": 0.05,
    "salary_consistency": 0.10,
    "identity_similarity": 0.10,
    "employer_consistency": 0.10
}

class SimilarityEngine:
    """
    Forensic similarity engine utilizing Case-Based Reasoning (CBR).
    Compares completed investigations against known dataset references (clean & fraud).
    """

    def __init__(self):
        # Pre-compiled feature vectors for reference cases in the dataset (to avoid expensive OCR during E2E requests)
        self.reference_cases = [
            # Genuine/Clean Cases
            {
                "id": "ref-clean-hdfc",
                "filename": "461790262-335063360-Hdfc-Bank-Statement-pdf.pdf",
                "label": "Genuine HDFC Bank Statement",
                "is_fraud": False,
                "trust_score": 100.0,
                "confidence_score": 95.0,
                "ocr_confidence": 100.0,
                "metadata_score": 100.0,
                "pdf_producer": "Mac OS X 10.15.7 Quartz PDFContext",
                "editing_software": "None",
                "compression": False,
                "ela_score": 0.0,
                "revision_count": 1,
                "salary_consistency": True,
                "identity_similarity": 1.0,
                "employer_consistency": 1.0,
                "document_count": 1,
                "context": "Mortgage Underwriting"
            },
            {
                "id": "ref-clean-boi",
                "filename": "590283501-BANK-OF-INDIA-2.pdf",
                "label": "Genuine Bank of India Statement",
                "is_fraud": False,
                "trust_score": 100.0,
                "confidence_score": 90.0,
                "ocr_confidence": 100.0,
                "metadata_score": 100.0,
                "pdf_producer": "Acrobat Distiller",
                "editing_software": "None",
                "compression": False,
                "ela_score": 0.0,
                "revision_count": 1,
                "salary_consistency": True,
                "identity_similarity": 1.0,
                "employer_consistency": 1.0,
                "document_count": 1,
                "context": "Loan Approval"
            },
            {
                "id": "ref-clean-canara",
                "filename": "652591331-Canara-Bank-Statement.pdf",
                "label": "Genuine Canara Bank Statement",
                "is_fraud": False,
                "trust_score": 100.0,
                "confidence_score": 95.0,
                "ocr_confidence": 100.0,
                "metadata_score": 100.0,
                "pdf_producer": "Microsoft Office PDF",
                "editing_software": "None",
                "compression": False,
                "ela_score": 0.0,
                "revision_count": 1,
                "salary_consistency": True,
                "identity_similarity": 1.0,
                "employer_consistency": 1.0,
                "document_count": 1,
                "context": "Tenant Screening"
            },
            # Fraudulent/Tampered Cases
            {
                "id": "ref-fraud-canara",
                "filename": "855219459-canara-bank-statement.pdf",
                "label": "Tampered Canara Statement (Font/Metadata Altered)",
                "is_fraud": True,
                "trust_score": 35.0,
                "confidence_score": 85.0,
                "ocr_confidence": 100.0,
                "metadata_score": 40.0,
                "pdf_producer": "Canva",
                "editing_software": "Canva",
                "compression": True,
                "ela_score": 45.0,
                "revision_count": 3,
                "salary_consistency": False,
                "identity_similarity": 0.50,
                "employer_consistency": 0.40,
                "document_count": 1,
                "context": "Mortgage Underwriting"
            },
            {
                "id": "ref-fraud-chase",
                "filename": "Chase bank statement.pdf",
                "label": "Forged Chase Bank Statement (Math Mismatch)",
                "is_fraud": True,
                "trust_score": 45.0,
                "confidence_score": 90.0,
                "ocr_confidence": 100.0,
                "metadata_score": 80.0,
                "pdf_producer": "iText",
                "editing_software": "Acrobat",
                "compression": False,
                "ela_score": 10.0,
                "revision_count": 2,
                "salary_consistency": True,
                "identity_similarity": 1.0,
                "employer_consistency": 1.0,
                "document_count": 1,
                "context": "Loan Approval"
            },
            {
                "id": "ref-fraud-xwd",
                "filename": "xwd.jpg",
                "label": "Altered Image Paystub (Pixel ELA Anomaly)",
                "is_fraud": True,
                "trust_score": 50.0,
                "confidence_score": 65.0,
                "ocr_confidence": 75.0,
                "metadata_score": 60.0,
                "pdf_producer": "None",
                "editing_software": "Photoshop",
                "compression": True,
                "ela_score": 85.0,
                "revision_count": 1,
                "salary_consistency": True,
                "identity_similarity": 1.0,
                "employer_consistency": 1.0,
                "document_count": 1,
                "context": "Employment Verification"
            }
        ]

    def generate_feature_vector(self, db: Session, investigation: Investigation) -> Dict[str, Any]:
        """
        Extracts forensic features from the completed investigation data and returns a normalized dictionary.
        """
        # Default scores
        trust = investigation.trust_score if investigation.trust_score is not None else 100.0
        doc_count = len(investigation.documents)
        
        # 1. OCR Confidence
        ocr_scores = []
        is_scanned_list = []
        for doc in investigation.documents:
            meta = doc.metadata_json or {}
            ocr_scores.append(meta.get("ocr_confidence", 100.0))
            is_scanned_list.append(meta.get("is_scanned", False))
        avg_ocr = sum(ocr_scores) / len(ocr_scores) if ocr_scores else 100.0
        
        # 2. Metadata integrity & tool detection
        metadata_score = 100.0
        producer = "None"
        editor = "None"
        revisions = 1
        compression = False
        ela_score = 0.0
        
        # Parse document metadata
        for doc in investigation.documents:
            meta = doc.metadata_json or {}
            raw_meta = meta.get("raw_metadata") or {}
            if raw_meta:
                # Producer detection
                candidate_prod = raw_meta.get("producer") or raw_meta.get("/Producer") or ""
                if candidate_prod:
                    producer = str(candidate_prod)
                
                # Creator/Editor detection
                creator = raw_meta.get("creator") or raw_meta.get("/Creator") or ""
                if creator:
                    editor = str(creator)
                
                # Check for suspicious editors (Photoshop/Canva/Illustrator)
                suspicious_tools = ["canva", "photoshop", "illustrator", "inkscape", "gimp", "acrobat"]
                if any(tool in producer.lower() for tool in suspicious_tools) or any(tool in editor.lower() for tool in suspicious_tools):
                    metadata_score = max(0.0, metadata_score - 40.0)
                    if editor == "None":
                        editor = producer
            
        # Inspect findings for metadata issues
        findings = investigation.findings
        for f in findings:
            if f.layer_source == "FORENSIC":
                # Deduct metadata score for forensic alerts
                metadata_score = max(0.0, metadata_score - 20.0)
                if "photoshop" in f.description.lower() or "canva" in f.description.lower():
                    editor = "Photo/Design Editor"
                if "ela" in f.name.lower() or "error level" in f.description.lower():
                    compression = True
                    ela_score = 80.0
                    
        # 3. Cross-Document details
        salary_consistency = True
        identity_similarity = 1.0
        employer_consistency = 1.0
        
        for f in findings:
            if f.layer_source == "CROSS_DOC":
                if "salary" in f.name.lower() or "income" in f.name.lower():
                    salary_consistency = False
                elif "identity" in f.name.lower() or "name" in f.name.lower():
                    # Attempt to extract similarity score from metadata_json
                    meta = f.metadata_json or {}
                    if isinstance(meta, dict) and "similarity_score" in meta:
                        identity_similarity = float(meta["similarity_score"])
                    else:
                        identity_similarity = 0.60
                elif "employer" in f.name.lower():
                    meta = f.metadata_json or {}
                    if isinstance(meta, dict) and "similarity_score" in meta:
                        employer_consistency = float(meta["similarity_score"])
                    else:
                        employer_consistency = 0.50
                        
        return {
            "trust_score": trust,
            "ocr_confidence": avg_ocr,
            "metadata_score": metadata_score,
            "pdf_producer": producer,
            "editing_software": editor,
            "compression": compression,
            "ela_score": ela_score,
            "revision_count": revisions,
            "salary_consistency": salary_consistency,
            "identity_similarity": identity_similarity,
            "employer_consistency": employer_consistency,
            "document_count": doc_count,
            "context": investigation.context
        }

    def compute_similarity(self, vec1: Dict[str, Any], vec2: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Calculates similarity score (0 to 100) and feature differences list.
        Uses a weighted comparison logic.
        """
        diffs = []
        weighted_sum = 0.0
        total_weight = 0.0

        for key, weight in FEATURE_WEIGHTS.items():
            total_weight += weight
            v1 = vec1.get(key)
            v2 = vec2.get(key)

            # Handle boolean features
            if isinstance(v1, bool) and isinstance(v2, bool):
                score = 1.0 if v1 == v2 else 0.0
                if v1 != v2:
                    diffs.append(f"{key.replace('_', ' ').title()} discrepancy: case has {v1}, target reference has {v2}.")
            # Handle numeric features (normalize scale 0-100 or 0-1)
            elif isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                # Adjust scale if it's 0-100 vs 0-1
                max_val = 100.0 if key in ["trust_score", "confidence_score", "ocr_confidence", "metadata_score"] else 1.0
                if key == "revision_count":
                    max_val = max(1.0, float(max(v1, v2)))
                
                diff = abs(float(v1) - float(v2)) / max_val
                score = max(0.0, 1.0 - diff)
                
                # Check for significant difference to explain
                if diff > 0.15:
                    diffs.append(f"{key.replace('_', ' ').title()} varies by {round(diff * max_val, 1)} points.")
            else:
                score = 1.0 # default if data is missing
                
            weighted_sum += score * weight

        # String matching comparisons (Bonus modifications)
        string_match_score = 0.0
        # Producer exact match bonus
        if vec1.get("pdf_producer") == vec2.get("pdf_producer") and vec1.get("pdf_producer") != "None":
            string_match_score += 0.05
        # Editor match
        if vec1.get("editing_software") == vec2.get("editing_software") and vec1.get("editing_software") != "None":
            string_match_score += 0.05
        # Context match
        if vec1.get("context") == vec2.get("context"):
            string_match_score += 0.10
            
        final_similarity = (weighted_sum / total_weight) * 100.0
        final_similarity = min(100.0, final_similarity + (string_match_score * 100.0))

        return round(final_similarity, 1), diffs

    def search_similar_cases(self, db: Session, investigation: Investigation) -> Dict[str, Any]:
        """
        Executes comparison of current investigation against all references and db history.
        """
        from core.settings_store import settings_store

        target_vec = self.generate_feature_vector(db, investigation)
        baseline_threshold = float(settings_store.get("baseline_similarity_threshold", 60.0))
        
        genuine_matches = []
        fraud_matches = []
        
        # 1. Compare against pre-compiled dataset references
        for ref in self.reference_cases:
            score, diffs = self.compute_similarity(target_vec, ref)
            match_entry = {
                "id": ref["id"],
                "filename": ref["filename"],
                "label": ref["label"],
                "similarity_score": score,
                "differences": diffs,
                "trust_score": ref["trust_score"],
                "is_fraud": ref["is_fraud"]
            }
            if ref["is_fraud"]:
                fraud_matches.append(match_entry)
            else:
                genuine_matches.append(match_entry)

        # 2. Compare against past investigations in DB
        db_cases = db.query(Investigation).filter(
            Investigation.id != investigation.id,
            Investigation.status == "COMPLETED"
        ).all()
        
        for db_case in db_cases:
            db_vec = self.generate_feature_vector(db, db_case)
            score, diffs = self.compute_similarity(target_vec, db_vec)
            
            # Determine fraud classification based on trust score
            is_fraud_case = db_case.trust_score is not None and db_case.trust_score < 70
            
            match_entry = {
                "id": db_case.id,
                "filename": f"Investigation: {db_case.title}",
                "label": f"DB Investigation (Trust: {db_case.trust_score}%)",
                "similarity_score": score,
                "differences": diffs,
                "trust_score": db_case.trust_score or 100.0,
                "is_fraud": is_fraud_case
            }
            if is_fraud_case:
                fraud_matches.append(match_entry)
            else:
                genuine_matches.append(match_entry)

        # 3. Compare against manually approved trusted repository entries
        try:
            from trusted_repository.repository_manager import repository_manager
            for entry in repository_manager.get_all_features():
                features = entry.get("features") or {}
                metadata = entry.get("metadata") or {}
                if metadata.get("investigation_id") == investigation.id:
                    continue
                score, diffs = self.compute_similarity(target_vec, features)
                genuine_matches.append({
                    "id": metadata.get("investigation_id", metadata.get("id", "trusted-reference")),
                    "filename": metadata.get("title", "Trusted Reference Investigation"),
                    "label": "Manually Approved Trusted Baseline",
                    "similarity_score": score,
                    "differences": diffs,
                    "trust_score": features.get("trust_score", 100.0),
                    "is_fraud": False
                })
        except Exception as exc:
            logger.warning(f"Trusted repository comparison skipped: {exc}")

        # Sort matches by similarity descending
        genuine_matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        fraud_matches.sort(key=lambda x: x["similarity_score"], reverse=True)

        top_genuine = [m for m in genuine_matches if m["similarity_score"] >= baseline_threshold][:2]
        top_fraud = [m for m in fraud_matches if m["similarity_score"] >= baseline_threshold][:2]
        
        # Best overall match selection
        best_match = None
        if top_genuine and top_fraud:
            if top_genuine[0]["similarity_score"] >= top_fraud[0]["similarity_score"]:
                best_match = top_genuine[0]
            else:
                best_match = top_fraud[0]
        elif top_genuine:
            best_match = top_genuine[0]
        elif top_fraud:
            best_match = top_fraud[0]

        similarity_score = best_match["similarity_score"] if best_match else 0.0
        is_closest_fraud = best_match["is_fraud"] if best_match else False
        
        explanation = "The current case exhibits structural characteristics similar to past genuine templates."
        if is_closest_fraud:
            explanation = f"High correlation detected with historical tampered templates (Match: {best_match['filename']}). Review editing indicators."
        elif not best_match:
            explanation = f"No reference case met the configured {baseline_threshold}% baseline similarity threshold."

        return {
            "feature_vector": target_vec,
            "similarity_score": similarity_score,
            "similarity_threshold": baseline_threshold,
            "is_closest_fraud": is_closest_fraud,
            "explanation": explanation,
            "top_similar_genuine": top_genuine,
            "top_similar_fraud": top_fraud
        }

similarity_engine = SimilarityEngine()
