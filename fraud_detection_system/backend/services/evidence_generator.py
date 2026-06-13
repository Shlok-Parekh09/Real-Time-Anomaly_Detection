from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models.database import Evidence, Finding, Document
import uuid

class EvidenceGenerator:
    """
    Automatically generates Evidence records linked to Findings by searching
    through document extraction results for relevant text.
    """
    
    def generate_evidence(
        self,
        db: Session,
        finding_id: str,
        investigation_id: str,
        involved_docs: List[Dict[str, Any]],
        description_prefix: str = ""
    ) -> List[Evidence]:
        """
        Creates Evidence records for a finding.
        involved_docs: List of dicts with {doc_id: str, search_text: str, label: str}
        """
        evidence_records = []
        
        for doc_info in involved_docs:
            doc_id = doc_info["doc_id"]
            search_text = str(doc_info["search_text"])
            label = doc_info["label"]
            
            # Fetch document data to find coordinates
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                continue
                
            # Search for text in coordinates (pre-extracted in Phase 2)
            # doc.entities_json usually stores coordinates or we search doc.metadata_json
            # For this implementation, we assume extraction_service stored 'coordinates' in doc.metadata_json
            coords = doc.metadata_json.get("coordinates", []) if doc.metadata_json else []
            
            # Find the first matching coordinate entry
            match = next((c for c in coords if search_text.lower() in c.get("text", "").lower()), None)
            
            evidence = Evidence(
                id=str(uuid.uuid4()),
                finding_id=finding_id,
                document_id=doc_id,
                page_number=match.get("page", 1) if match else 1,
                coordinates=match.get("bbox") if match else None,
                confidence=match.get("confidence", 0.95) if match else 0.8,
                extracted_text=search_text,
                description=f"{description_prefix} {label}: {search_text}".strip()
            )
            db.add(evidence)
            evidence_records.append(evidence)
            
        db.commit()
        return evidence_records

evidence_generator = EvidenceGenerator()
