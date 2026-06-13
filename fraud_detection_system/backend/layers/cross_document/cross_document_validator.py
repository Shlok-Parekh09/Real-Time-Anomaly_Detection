from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models.database import Finding, Document
from .normalizer import normalizer
from services.evidence_generator import evidence_generator
import uuid

class CrossDocumentValidator:
    """
    Core engine for multi-document consistency validation.
    """
    
    def validate_investigation(self, db: Session, investigation_id: str) -> List[Finding]:
        """
        Runs the full cross-document suite for an investigation.
        """
        findings = []
        docs = db.query(Document).filter(Document.investigation_id == investigation_id).all()
        if len(docs) < 2:
            return findings

        # Convert ORM to list of dicts for easier processing
        docs_data = []
        for d in docs:
            docs_data.append({
                "id": d.id,
                "filename": d.filename,
                "classification": d.classification,
                "entities": d.entities_json or {},
                "extracted_text": d.extracted_text
            })

        # Run checks
        findings.extend(self._check_identity_consistency(db, investigation_id, docs_data))
        findings.extend(self._check_employer_consistency(db, investigation_id, docs_data))
        findings.extend(self._check_salary_consistency(db, investigation_id, docs_data))

        return findings

    def _check_identity_consistency(self, db: Session, investigation_id: str, docs: List[Dict[str, Any]]) -> List[Finding]:
        findings = []
        
        # 1. Name Consistency
        name_map = {d["id"]: d["entities"].get("name") for d in docs if d["entities"].get("name")}
        if len(name_map) >= 2:
            doc_ids = list(name_map.keys())
            for i in range(len(doc_ids)):
                for j in range(i + 1, len(doc_ids)):
                    id1, id2 = doc_ids[i], doc_ids[j]
                    n1, n2 = name_map[id1], name_map[id2]
                    
                    norm1 = normalizer.normalize_name(n1)
                    norm2 = normalizer.normalize_name(n2)
                    
                    sim = normalizer.calculate_similarity(norm1, norm2)
                    # Handle abbreviation fallback
                    if sim < 0.92:
                        sim = max(sim, normalizer.handle_abbreviation(n1, n2), normalizer.handle_abbreviation(n2, n1))
                    
                    if sim < 0.85:
                        finding = self._create_finding(
                            db, investigation_id, "Identity Name Mismatch", "HIGH",
                            f"Name inconsistency detected between {self._get_fn(docs, id1)} and {self._get_fn(docs, id2)}.",
                            {"similarity_score": sim, "method": "jaro_winkler_with_abbr"}
                        )
                        evidence_generator.generate_evidence(db, finding.id, investigation_id, [
                            {"doc_id": id1, "search_text": n1, "label": "Name on Document"},
                            {"doc_id": id2, "search_text": n2, "label": "Name on Document"}
                        ])
                        findings.append(finding)

        # 2. PAN Consistency
        pan_map = {d["id"]: d["entities"].get("pan") for d in docs if d["entities"].get("pan")}
        if len(set(pan_map.values())) > 1:
            # Simple mismatch for exact IDs
            items = list(pan_map.items())
            finding = self._create_finding(
                db, investigation_id, "PAN Identifier Mismatch", "HIGH",
                "Different PAN numbers detected across documents.",
                {"similarity_score": 0.0}
            )
            evidence_generator.generate_evidence(db, finding.id, investigation_id, [
                {"doc_id": k, "search_text": v, "label": "PAN Number"} for k, v in items
            ])
            findings.append(finding)

        return findings

    def _check_employer_consistency(self, db: Session, investigation_id: str, docs: List[Dict[str, Any]]) -> List[Finding]:
        findings = []
        emp_map = {d["id"]: d["entities"].get("employer") for d in docs if d["entities"].get("employer")}
        
        if len(emp_map) >= 2:
            ids = list(emp_map.keys())
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    id1, id2 = ids[i], ids[j]
                    e1, e2 = emp_map[id1], emp_map[id2]
                    
                    sim = normalizer.calculate_similarity(normalizer.normalize_employer(e1), normalizer.normalize_employer(e2), method="token_set_ratio")
                    
                    if sim < 0.75:
                        finding = self._create_finding(
                            db, investigation_id, "Employer Mismatch", "MEDIUM",
                            "Inconsistent employer names detected across documents.",
                            {"similarity_score": sim, "method": "token_set_ratio"}
                        )
                        evidence_generator.generate_evidence(db, finding.id, investigation_id, [
                            {"doc_id": id1, "search_text": e1, "label": "Employer Name"},
                            {"doc_id": id2, "search_text": e2, "label": "Employer Name"}
                        ])
                        findings.append(finding)
        return findings

    def _check_salary_consistency(self, db: Session, investigation_id: str, docs: List[Dict[str, Any]]) -> List[Finding]:
        findings = []
        payslip_salaries = {d["id"]: d["entities"].get("salary") for d in docs if d["classification"] == "Payslip" and d["entities"].get("salary")}
        
        # In a full impl, we'd look for bank statement transaction matches here.
        # For now, we compare multiple payslips if present.
        if len(payslip_salaries) >= 2:
            ids = list(payslip_salaries.keys())
            v1, v2 = payslip_salaries[ids[0]], payslip_salaries[ids[1]]
            diff = abs(v1 - v2)
            if diff > 100: # Threshold for mismatch
                finding = self._create_finding(
                    db, investigation_id, "Income Consistency Failure", "HIGH",
                    "Net pay amounts differ across multiple payslips.",
                    {"variance": diff}
                )
                evidence_generator.generate_evidence(db, finding.id, investigation_id, [
                    {"doc_id": ids[0], "search_text": v1, "label": "Reported Salary"},
                    {"doc_id": ids[1], "search_text": v2, "label": "Reported Salary"}
                ])
                findings.append(finding)
        return findings

    def _create_finding(self, db: Session, investigation_id: str, name: str, severity: str, desc: str, metadata: Dict[str, Any]) -> Finding:
        finding = Finding(
            id=str(uuid.uuid4()),
            investigation_id=investigation_id,
            layer_source="CROSS_DOC",
            name=name,
            severity=severity,
            description=desc,
            metadata_json=metadata
        )
        db.add(finding)
        db.commit()
        return finding

    def _get_fn(self, docs: List[Dict[str, Any]], doc_id: str) -> str:
        return next((d["filename"] for d in docs if d["id"] == doc_id), "Document")

cross_document_validator = CrossDocumentValidator()
