"""
Text Coordinate Extractor
Extracts exact text positions with bounding boxes for precise highlighting
ONLY highlights specific suspicious values from HIGH severity fraud signals
"""

from __future__ import annotations

import io
import re
from typing import Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


def extract_pdf_text_coordinates(pdf_bytes: bytes, search_terms: list[str]) -> list[dict[str, Any]]:
    """
    Extract exact coordinates of specific text in PDF.
    Returns bounding boxes for each occurrence of search terms.
    """
    if not PYMUPDF_AVAILABLE:
        print("[PDF_COORD] PyMuPDF not available")
        return []
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        coordinates = []
        
        print(f"[PDF_COORD] Processing {len(doc)} pages, searching for {len(search_terms)} terms")
        if search_terms:
            print(f"[PDF_COORD] Search terms: {search_terms[:10]}")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_height = page.rect.height
            page_width = page.rect.width
            
            # Use PyMuPDF's search_for method for exact matching
            for term in search_terms:
                if not term or len(term.strip()) < 2:
                    continue
                
                text_instances = page.search_for(term.strip())
                
                if text_instances:
                    print(f"[PDF_COORD] Found {len(text_instances)} instances of '{term}' on page {page_num + 1}")
                
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
                        }
                    })
        
        doc.close()
        print(f"[PDF_COORD] Total coordinates found: {len(coordinates)}")
        
        return coordinates
        
    except Exception as e:
        print(f"[PDF_COORD] PDF text coordinate extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_image_text_coordinates(image_bytes: bytes, search_terms: list[str]) -> list[dict[str, Any]]:
    """
    Extract exact coordinates of specific text in images using OCR.
    Returns bounding boxes for each occurrence of search terms.
    """
    if not PYTESSERACT_AVAILABLE:
        return []
    
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_width, image_height = image.size
        
        # Get OCR data with bounding boxes
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        coordinates = []
        
        # Build a map of text to coordinates
        for i, word in enumerate(ocr_data['text']):
            word_clean = word.strip()
            if not word_clean:
                continue
            
            # Check if this word matches any search term
            for term in search_terms:
                term_clean = term.strip().lower()
                if not term_clean or len(term_clean) < 2:
                    continue
                
                # Check for exact match or partial match
                if term_clean in word_clean.lower() or word_clean.lower() in term_clean:
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    # Convert to percentage-based coordinates
                    coordinates.append({
                        "page": 1,  # Images are single page
                        "text": word_clean,
                        "matched_term": term.strip(),
                        "confidence": float(ocr_data['conf'][i]) if ocr_data['conf'][i] != -1 else 0,
                        "bbox": {
                            "x": (x / image_width) * 100,
                            "y": (y / image_height) * 100,
                            "width": (w / image_width) * 100,
                            "height": (h / image_height) * 100,
                        },
                        "bbox_pixels": {
                            "x": x,
                            "y": y,
                            "width": w,
                            "height": h,
                        }
                    })
        
        return coordinates
        
    except Exception as e:
        print(f"Image text coordinate extraction failed: {e}")
        return []


def get_fraud_signal_coordinates(
    document_bytes: bytes,
    file_type: str,
    fraud_signals: list[dict[str, Any]],
    extracted_text: str
) -> list[dict[str, Any]]:
    """
    Get coordinates for fraud signals.
    Extracts numeric values from HIGH severity signals and highlights them.
    """
    print(f"[COORD_EXTRACT] Starting coordinate extraction for {file_type}")
    print(f"[COORD_EXTRACT] Number of fraud signals: {len(fraud_signals)}")
    
    # Extract numeric values from HIGH severity signals
    search_terms = []
    high_severity_signals = [s for s in fraud_signals if s.get('severity') == 'high']
    
    print(f"[COORD_EXTRACT] High severity signals: {len(high_severity_signals)}")
    
    for signal in high_severity_signals:
        signal_name = signal.get('name', '')
        evidence = signal.get('evidence', [])
        
        print(f"[COORD_EXTRACT] Processing signal: {signal_name}")
        
        for item in evidence:
            # Parse evidence item to extract numeric values
            item_dict = None
            
            if isinstance(item, dict):
                item_dict = item
            elif isinstance(item, str):
                # Try to parse string representation of dict
                if item.strip().startswith('{'):
                    try:
                        import ast
                        item_dict = ast.literal_eval(item)
                        print(f"[COORD_EXTRACT] Parsed dict from string")
                    except (ValueError, SyntaxError):
                        # If parsing fails, try to extract numbers directly from string
                        # Look for arrays of numbers: [20000.0, 3000.0, 5000.0]
                        array_match = re.search(r'\[([\d.,\s]+)\]', item)
                        if array_match:
                            amounts_str = array_match.group(1)
                            try:
                                amounts = [float(x.strip()) for x in amounts_str.split(',') if x.strip()]
                                item_dict = {'extracted_values': amounts}
                                print(f"[COORD_EXTRACT] Extracted {len(amounts)} values via regex")
                            except ValueError:
                                pass
            
            # Extract numeric values from the dict
            if item_dict:
                extracted_amounts = []
                
                # Recursively extract all numeric values from the dict
                def extract_numbers(obj):
                    if isinstance(obj, (int, float)):
                        return [float(obj)]
                    elif isinstance(obj, list):
                        numbers = []
                        for item in obj:
                            numbers.extend(extract_numbers(item))
                        return numbers
                    elif isinstance(obj, dict):
                        numbers = []
                        for key, value in obj.items():
                            # Skip metadata keys
                            if key in ['type', 'severity', 'description']:
                                continue
                            numbers.extend(extract_numbers(value))
                        return numbers
                    return []
                
                extracted_amounts = extract_numbers(item_dict)
                
                # Filter to only amounts >= 1000 (to avoid highlighting dates, small numbers)
                extracted_amounts = [a for a in extracted_amounts if a >= 1000]
                
                if extracted_amounts:
                    print(f"[COORD_EXTRACT] Found {len(extracted_amounts)} amounts: {extracted_amounts[:5]}")
                    
                    # Only take first 3 amounts to avoid highlighting too much
                    for amount in extracted_amounts[:3]:
                        # Generate format variations that might appear in the document
                        # Format 1: With comma (20,000)
                        formatted_comma = f"{int(amount):,}"
                        search_terms.append(formatted_comma)
                        
                        # Format 2: With comma and .00 (20,000.00)
                        search_terms.append(f"{formatted_comma}.00")
                        
                        print(f"[COORD_EXTRACT] Added search terms: {formatted_comma}, {formatted_comma}.00")
    
    # Remove duplicates
    search_terms = list(dict.fromkeys(search_terms))
    
    # Limit to top 10 to avoid highlighting too much
    search_terms = search_terms[:10]
    
    print(f"[COORD_EXTRACT] Final search terms ({len(search_terms)}): {search_terms}")
    
    if not search_terms:
        print(f"[COORD_EXTRACT] No search terms found, skipping highlighting")
        return []
    
    # Extract coordinates
    if file_type == 'pdf':
        coordinates = extract_pdf_text_coordinates(document_bytes, search_terms)
    elif file_type == 'image':
        coordinates = extract_image_text_coordinates(document_bytes, search_terms)
    else:
        coordinates = []
    
    print(f"[COORD_EXTRACT] Found {len(coordinates)} coordinates")
    
    # Map coordinates to signals
    result = []
    for coord in coordinates:
        # Find the high severity signal this belongs to
        matched_signal = high_severity_signals[0] if high_severity_signals else None
        
        if matched_signal:
            result.append({
                **coord,
                "signal_id": matched_signal.get('id'),
                "signal_name": matched_signal.get('name'),
                "severity": matched_signal.get('severity', 'high'),
            })
    
    print(f"[COORD_EXTRACT] Returning {len(result)} highlight regions")
    
    return result


def get_smart_highlight_regions(
    document_bytes: bytes,
    file_type: str,
    fraud_signals: list[dict[str, Any]],
    extracted_text: str
) -> list[dict[str, Any]]:
    """
    Get smart highlight regions based on fraud signals.
    Returns regions with exact coordinates for highlighting.
    """
    coordinates = get_fraud_signal_coordinates(
        document_bytes, file_type, fraud_signals, extracted_text
    )
    
    # Convert coordinates to regions (no merging to keep highlights precise)
    regions = []
    for coord in coordinates:
        regions.append({
            "page": coord.get('page', 1),
            "bbox": coord['bbox'],
            "severity": coord.get('severity', 'high'),
            "signal_name": coord.get('signal_name', 'Unknown'),
            "signal_id": coord.get('signal_id', ''),
            "text": coord.get('text', ''),
        })
    
    print(f"[HIGHLIGHTING] Extracted {len(regions)} highlight regions for {file_type}")
    
    return regions
