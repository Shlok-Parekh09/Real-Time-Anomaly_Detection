from typing import List, Dict, Any, Tuple
from models.database import Finding, Document
from core.config import settings

class TrustEngine:
    """
    Calculates Trust score based on findings.
    Generates actionable recommendations for investigators.
    """
    
    # Deduction Configuration
    SEVERITY_DEDUCTIONS = {
        "HIGH": (30, 40),
        "MEDIUM": (15, 20),
        "LOW": (5, 10)
    }
    
    # Source Multipliers
    SOURCE_MULTIPLIERS = {
        "FORENSIC": 1.0,
        "CROSS_DOC": 0.9,
        "CONTEXT": 0.8,
        "KNN": 0.5
    }

    # Deduction Caps
    DEDUCTION_CAPS = {
        "LOW": 25.0,
        "MEDIUM": 50.0
    }

    def calculate_scores(
        self, 
        findings: List[Dict[str, Any]], 
        extraction_metrics: Dict[str, Any],
        expected_docs_count: int,
        actual_docs_count: int
    ) -> Tuple[float, Optional[float], str]:
        """
        Calculates Trust Score and Recommendation. Confidence score is deprecated.
        """
        trust_score = self._calculate_trust_score(findings, expected_docs_count, actual_docs_count)
        recommendation = self._generate_recommendation(trust_score, None)
        
        return trust_score, None, recommendation

    def _calculate_trust_score(self, findings: List[Dict[str, Any]], expected: int, actual: int) -> float:
        score = 100.0
        
        # 1. Group deductions by severity for capping
        deductions = {"HIGH": 0.0, "MEDIUM": 0.0, "LOW": 0.0}
        
        for f in findings:
            severity = f.get("severity", "LOW").upper()
            source = f.get("layer_source", "CONTEXT").upper()
            
            # Use middle of range for base deduction
            base_deduction = (self.SEVERITY_DEDUCTIONS[severity][0] + self.SEVERITY_DEDUCTIONS[severity][1]) / 2
            multiplier = self.SOURCE_MULTIPLIERS.get(source, 1.0)
            
            deductions[severity] += base_deduction * multiplier

        # 2. Apply Caps
        total_deduction = deductions["HIGH"] # Uncapped
        total_deduction += min(deductions["MEDIUM"], self.DEDUCTION_CAPS["MEDIUM"])
        total_deduction += min(deductions["LOW"], self.DEDUCTION_CAPS["LOW"])
        
        score -= total_deduction

        # 3. Apply Bonuses
        if actual >= expected and expected > 0:
            score += 5.0 # All expected docs present
            
        # Bonus for strong cross-doc consistency (if no HIGH/MEDIUM cross-doc findings)
        cross_doc_anomalies = [f for f in findings if f["layer_source"] == "CROSS_DOC" and f["severity"] in ["HIGH", "MEDIUM"]]
        if not cross_doc_anomalies and any(f["layer_source"] == "CROSS_DOC" for f in findings):
             score += 5.0

        return max(0.0, min(100.0, round(score, 1)))

    def _calculate_confidence_score(self, metrics: Dict[str, Any], expected: int, actual: int) -> float:
        """
        OCR_Quality * 0.4 + Entity_Success * 0.4 + Evidence_Clarity * 0.2
        """
        ocr_quality = metrics.get("ocr_quality", 100.0) # 0-100
        entity_success = metrics.get("entity_success_rate", 100.0) # 0-100
        evidence_clarity = metrics.get("evidence_clarity", 100.0) # 0-100
        
        score = (ocr_quality * 0.4) + (entity_success * 0.4) + (evidence_clarity * 0.2)
        
        # Penalty for missing documents
        if actual < expected:
            score -= 20.0
            
        # Penalty for poor image quality (OCR confidence < 60)
        if metrics.get("poor_image_quality", False):
            score -= 10.0
            
        return max(0.0, min(100.0, round(score, 1)))

    def _generate_recommendation(self, trust: float, confidence: float) -> str:
        """
        Logic:
        - Read auto_approve_cases and min_trust_threshold from settings_store.
        """
        from core.settings_store import settings_store
        auto_approve = settings_store.get("auto_approve_cases", True)
        min_trust = settings_store.get("min_trust_threshold", 85.0)

        if auto_approve and trust >= min_trust:
            return "AUTO_APPROVE"
            
        if trust < 50:
            return "HIGH_RISK_MANUAL_REVIEW"
            
        return "MANUAL_REVIEW"

trust_engine = TrustEngine()
