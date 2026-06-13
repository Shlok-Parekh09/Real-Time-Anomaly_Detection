from typing import Dict, Any, List
from models.database import Investigation
import json

class ReportGenerator:
    """
    Generates structured audit-ready reports for investigations.
    """
    
    def generate_json_report(self, investigation: Investigation) -> Dict[str, Any]:
        """
        Creates a comprehensive JSON structure for the frontend and archival.
        """
        report = {
            "investigation_id": investigation.id,
            "context": investigation.context,
            "status": investigation.status,
            "created_at": investigation.created_at.isoformat(),
            "scores": {
                "trust_score": investigation.trust_score,
                "confidence_score": investigation.confidence_score,
                "recommendation": investigation.recommendation
            },
            "ai_summary": investigation.ai_summary_json,
            "documents": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "classification": d.classification,
                    "file_type": d.file_type
                } for d in investigation.documents
            ],
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
                            "description": e.description,
                            "coordinates": e.coordinates
                        } for e in f.evidence_items
                    ]
                } for f in investigation.findings
            ],
            "timeline": [
                {
                    "timestamp": ev.timestamp.isoformat(),
                    "type": ev.event_type,
                    "message": ev.message
                } for ev in investigation.events
            ]
        }
        return report

    def generate_pdf_report(self, investigation: Investigation) -> bytes:
        """
        Placeholder for PDF generation (e.g., using ReportLab or WeasyPrint).
        Returns raw PDF bytes.
        """
        # In a full implementation, we'd render an HTML template to PDF.
        return b"%PDF-1.4 [Placeholder PDF Content]"

report_generator = ReportGenerator()
