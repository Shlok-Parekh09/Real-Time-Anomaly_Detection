import re
from typing import Dict, Any, List
from .pdf_analyzer import pdf_analyzer

class DigitalForensics:
    """
    Handles digital tampering detection for various file types.
    """
    
    def analyze(self, file_bytes: bytes, filename: str, content_type: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs digital forensic checks.
        """
        findings = []
        
        file_type = metadata.get("file_type", "unknown")
        
        if file_type == "pdf":
            findings.extend(pdf_analyzer.analyze_structure(file_bytes, metadata))
        elif file_type == "image":
            findings.extend(self._analyze_image_forensics(file_bytes, metadata))
            
        # Common metadata checks
        findings.extend(self._check_metadata_anomalies(metadata))
            
        return findings

    def _check_metadata_anomalies(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []
        producer = str(metadata.get("Producer", "")).lower()
        creator = str(metadata.get("Creator", "")).lower()
        
        suspicious_software = ["photoshop", "illustrator", "gimp", "canva", "quartz pdfcontext"]
        
        for software in suspicious_software:
            if software in producer or software in creator:
                anomalies.append({
                    "name": "Editing Software Signature",
                    "severity": "HIGH",
                    "description": f"Metadata contains traces of editing software: {software}",
                    "evidence": [f"Producer/Creator: {software}"]
                })
                
        # Date mismatch
        created = metadata.get("CreationDate")
        modified = metadata.get("ModDate")
        if created and modified and created != modified:
            anomalies.append({
                "name": "Metadata Date Mismatch",
                "severity": "MEDIUM",
                "description": "Document creation and modification dates are different, suggesting post-generation editing.",
                "evidence": [f"Created: {created}", f"Modified: {modified}"]
            })
            
        return anomalies

    def _analyze_image_forensics(self, file_bytes: bytes, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # This will call advanced_image_analysis logic later
        return []

digital_forensics = DigitalForensics()
