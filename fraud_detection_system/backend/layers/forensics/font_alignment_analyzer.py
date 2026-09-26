import re
from typing import Dict, Any, List

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

class FontAlignmentAnalyzer:
    """
    Analyzes PDF text blocks for font inconsistencies and alignment anomalies.
    """

    def analyze(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        if not PYMUPDF_AVAILABLE:
            return []

        findings = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            all_fonts = set()
            suspicious_fonts = ["arial", "timesnewroman", "helvetica", "calibri"]

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Check Font inconsistencies
                fonts = page.get_fonts()
                for font in fonts:
                    font_name = font[3].lower()
                    all_fonts.add(font_name)

                    # Heuristic: Detect if common consumer fonts exist alongside proprietary-looking fonts
                    # Or just flag the presence of standard fonts often used in edits
                    for susp_font in suspicious_fonts:
                        if susp_font in font_name:
                            findings.append({
                                "name": "Suspicious Consumer Font",
                                "severity": "MEDIUM",
                                "description": f"Standard font '{susp_font}' detected. Banks typically use proprietary fonts.",
                                "evidence": [f"Found font: {font_name}"]
                            })

                # Check Alignment Issues
                # A very basic heuristic: look for numbers that should be right-aligned but aren't
                # Or text blocks that are slightly off from the main column
                blocks = page.get_text("dict")["blocks"]
                x_coords = []
                for b in blocks:
                    if b['type'] == 0:  # text block
                        for l in b["lines"]:
                            for s in l["spans"]:
                                text = s["text"].strip()
                                if re.match(r'^[\d,\.]+$', text): # If it's a number
                                    x_coords.append(s["bbox"][0]) # left x coord

                if x_coords:
                    # Check if there are many unique slightly off x-coordinates
                    # In a perfect statement, amounts are perfectly aligned.
                    # We group coordinates within a 2px threshold.
                    grouped_x = []
                    for x in x_coords:
                        matched = False
                        for gx in grouped_x:
                            if abs(x - gx) < 2.0:
                                matched = True
                                break
                        if not matched:
                            grouped_x.append(x)

                    # If we have too many unique alignments for numbers, it might be tampered
                    if len(grouped_x) > 10 and len(x_coords) > 20:
                         findings.append({
                            "name": "Number Alignment Inconsistency",
                            "severity": "MEDIUM",
                            "description": "Found multiple misaligned number columns, suggesting manual editing.",
                            "evidence": [f"Found {len(grouped_x)} distinct horizontal alignment points for numbers."]
                        })

            if len(all_fonts) > 5:
                findings.append({
                    "name": "Font Inconsistencies",
                    "severity": "MEDIUM",
                    "description": "Unusually high number of distinct fonts found in the document, suggesting copy-paste editing.",
                    "evidence": [f"Fonts found: {', '.join(list(all_fonts)[:5])}..."]
                })

            doc.close()
            return findings
        except Exception as e:
            print(f"[FontAnalyzer] Error analyzing fonts: {e}")
            return []

font_alignment_analyzer = FontAlignmentAnalyzer()
