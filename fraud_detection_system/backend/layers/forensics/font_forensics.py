from typing import Dict, Any, List

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

class FontForensics:
    """
    Analyzes font consistency within PDFs.
    """
    def analyze(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        findings = []
        if not PYMUPDF_AVAILABLE:
            return findings

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            all_fonts = set()
            consumer_fonts = ["arial", "timesnewroman", "helvetica", "calibri", "courier"]
            found_consumer = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                fonts = page.get_fonts()
                for font in fonts:
                    font_name = font[3].lower()
                    all_fonts.add(font_name)
                    for cf in consumer_fonts:
                        if cf in font_name and font_name not in found_consumer:
                            found_consumer.append(font_name)

                # Basic Alignment drift check
                blocks = page.get_text("dict")["blocks"]
                decimal_x_coords = []
                for b in blocks:
                    if b['type'] == 0:
                        for l in b["lines"]:
                            for s in l["spans"]:
                                text = s["text"].strip()
                                if '.' in text and any(c.isdigit() for c in text): # Has decimal and numbers
                                    decimal_x_coords.append(s["bbox"][2]) # Right bounding box edge

                if decimal_x_coords:
                    # Group x-coords within 1.5px
                    groups = []
                    for x in decimal_x_coords:
                        matched = False
                        for gx in groups:
                            if abs(x - gx) < 1.5:
                                matched = True
                                break
                        if not matched:
                            groups.append(x)

                    if len(groups) > 5 and len(decimal_x_coords) > 10:
                        findings.append({
                            "name": "Decimal Alignment Drift",
                            "severity": "MEDIUM",
                            "description": "Detected multiple misaligned decimal points in numerical columns. Authentic tables typically align perfectly.",
                            "evidence": [f"Found {len(groups)} different vertical alignment points for decimals on page {page_num+1}."]
                        })

            if len(all_fonts) > 3:
                findings.append({
                    "name": "Font Inconsistencies",
                    "severity": "MEDIUM",
                    "description": "Unusually high number of distinct fonts. Banks typically use 1-2 proprietary fonts.",
                    "evidence": [f"Fonts found ({len(all_fonts)} total): {', '.join(list(all_fonts)[:5])}..."]
                })

            if found_consumer and len(all_fonts) > 1:
                findings.append({
                    "name": "Mixed Consumer & Proprietary Fonts",
                    "severity": "HIGH",
                    "description": "Detected standard consumer fonts mixed with other fonts. Fraudsters often use standard fonts to edit numbers.",
                    "evidence": [f"Standard fonts detected: {', '.join(found_consumer)}"]
                })

            doc.close()
            return findings
        except Exception as e:
            print(f"[FontForensics] Error: {e}")
            return findings

font_forensics = FontForensics()
