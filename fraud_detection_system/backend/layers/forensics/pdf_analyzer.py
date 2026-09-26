import re
from typing import Dict, Any, List

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

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
            

        # Check for Digital Signatures
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                # Bank statements often have a specific digital signature
                has_signature = False
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    widgets = page.widgets()
                    if widgets:
                        for widget in widgets:
                            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                                has_signature = True
                                break

                # A very crude string-based check if PyMuPDF widgets don't catch it
                if b"/ByteRange" in pdf_bytes and b"/Contents" in pdf_bytes and b"/Type /Sig" in pdf_bytes:
                    has_signature = True

                if not has_signature:
                     findings.append({
                        "name": "Missing Digital Signature",
                        "severity": "MEDIUM",
                        "description": "Authentic bank statements often carry a digital signature. None was found.",
                        "evidence": ["No cryptographic signature block detected in the PDF."]
                    })
                doc.close()
            except Exception as e:
                pass

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
