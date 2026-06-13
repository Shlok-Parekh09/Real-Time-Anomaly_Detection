import re
from typing import Dict, Any, List

class PDFAnalyzer:
    """
    Analyzes PDF structure for anomalies like incremental updates, hidden layers, etc.
    """
    
    def analyze_structure(self, pdf_bytes: bytes, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        
        # Check for incremental updates (Multiple %%EOF markers)
        eof_count = pdf_bytes.count(b"%%EOF")
        if eof_count > 1:
            findings.append({
                "name": "Multiple PDF Revisions",
                "severity": "HIGH",
                "description": f"This PDF contains {eof_count} revisions, which is common in manual tampering.",
                "evidence": [f"%%EOF markers found: {eof_count}"]
            })
            
        # Check for /Prev pointers
        prev_pointers = len(re.findall(rb"/Prev\s+\d+", pdf_bytes))
        if prev_pointers > 0:
            findings.append({
                "name": "PDF Incremental Update Trace",
                "severity": "MEDIUM",
                "description": "The PDF structure indicates it has been modified after initial creation.",
                "evidence": [f"Prev pointers found: {prev_pointers}"]
            })
            
        return findings

pdf_analyzer = PDFAnalyzer()
