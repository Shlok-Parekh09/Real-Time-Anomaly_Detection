"""
Text Coordinate Extractor
Extracts exact text positions with bounding boxes for precise highlighting
Highlights key forensic fields: account numbers, dates, names, addresses, and large amounts
"""

from __future__ import annotations

import re
from typing import Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def extract_forensic_field_coordinates(pdf_bytes: bytes, extracted_text: str) -> list[dict[str, Any]]:
    """
    Extract exact coordinates of forensic fields in PDF.
    Returns bounding boxes for account numbers, dates, names/addresses, and large amounts.
    """
    if not PYMUPDF_AVAILABLE:
        print("[PDF_COORD] PyMuPDF not available")
        return []
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        coordinates = []
        
        # Determine search patterns for forensic fields
        patterns = {
            "Account Number": [
                r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b',  # 16 digit card
                r'\b\d{9,12}\b',  # standard account numbers
            ],
            "Date": [
                r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
            ],
            "Amount": [
                r'\$[\d,]+\.\d{2}',
            ]
        }

        # Also search for names/addresses (often first few lines of text or block of capitalized words)
        # We'll just look for a few capitalized words in a row for "Name"
        name_pattern = r'\b[A-Z][a-z]+(?: [A-Z][a-z]+){1,3}\b'
        
        # Compile all patterns to search text
        search_terms = []
        for category, regex_list in patterns.items():
            for regex in regex_list:
                matches = re.findall(regex, extracted_text)
                for match in matches:
                    search_terms.append((match, category))
        
        # Find names (heuristic: capitalized words not at start of sentence, or just standard names)
        names = re.findall(name_pattern, extracted_text)
        for name in names:
            if len(name.split()) >= 2 and len(name) < 40:
                search_terms.append((name, "Name/Address"))

        # Deduplicate terms
        unique_terms = {}
        for term, cat in search_terms:
            if term not in unique_terms:
                unique_terms[term] = cat

        print(f"[PDF_COORD] Processing {len(doc)} pages, searching for {len(unique_terms)} fields")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_height = page.rect.height
            page_width = page.rect.width
            
            for term, category in unique_terms.items():
                if not term or len(term.strip()) < 2:
                    continue
                
                text_instances = page.search_for(term.strip())
                
                for rect in text_instances:
                    coordinates.append({
                        "page": page_num + 1,
                        "text": term.strip(),
                        "matched_term": term.strip(),
                        "bbox": {
                            "x": (rect.x0 / page_width) * 100,
                            "y": (rect.y0 / page_height) * 100,
                            "width": ((rect.x1 - rect.x0) / page_width) * 100,
                            "height": ((rect.y1 - rect.y0) / page_height) * 100,
                        },
                        "bbox_pixels": {
                            "x": rect.x0,
                            "y": rect.y0,
                            "width": rect.x1 - rect.x0,
                            "height": rect.y1 - rect.y0,
                        },
                        "signal_name": category,
                        "severity": "high",  # Highlight them all prominently
                    })
        
        doc.close()
        
        # To avoid highlighting too many amounts, limit amount highlights to the largest 10
        # and limit names to top 5
        amount_coords = [c for c in coordinates if c["signal_name"] == "Amount"]
        other_coords = [c for c in coordinates if c["signal_name"] != "Amount"]
        
        # Basic sorting to get unique ones
        seen = set()
        filtered_coords = []
        for c in other_coords + amount_coords[:15]:
            # Deduplicate by approximate position
            pos_key = f"{c['page']}_{round(c['bbox']['x'])}_{round(c['bbox']['y'])}"
            if pos_key not in seen:
                seen.add(pos_key)
                filtered_coords.append(c)

        print(f"[PDF_COORD] Total coordinates found: {len(filtered_coords)}")
        return filtered_coords
        
    except Exception as e:
        print(f"[PDF_COORD] PDF text coordinate extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_smart_highlight_regions(
    document_bytes: bytes,
    file_type: str,
    fraud_signals: list[dict[str, Any]],
    extracted_text: str
) -> list[dict[str, Any]]:
    """
    Get smart highlight regions based on forensic fields.
    Returns regions with exact coordinates for highlighting.
    """
    if file_type != 'pdf':
        return []
        
    coordinates = extract_forensic_field_coordinates(document_bytes, extracted_text)
    
    # Convert coordinates to regions
    regions = []
    for coord in coordinates:
        regions.append({
            "page": coord.get('page', 1),
            "bbox": coord['bbox'],
            "severity": coord.get('severity', 'high'),
            "signal_name": coord.get('signal_name', 'Forensic Field'),
            "signal_id": 'forensic_field',
            "text": coord.get('text', ''),
        })
    
    print(f"[HIGHLIGHTING] Extracted {len(regions)} highlight regions")
    
    return regions
