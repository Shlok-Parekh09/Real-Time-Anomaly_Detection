"""
Advanced PDF Analysis using PyMuPDF and PDFMiner
Detects unauthorized software modifications and extracts detailed metadata
"""

from __future__ import annotations

import io
import re
from collections import Counter
from datetime import datetime
from typing import Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdfdocument import PDFDocument
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False


# Known legitimate banking software
LEGITIMATE_PDF_CREATORS = [
    "microsoft word",
    "microsoft excel", 
    "libreoffice",
    "openoffice",
    "adobe acrobat",
    "pdftk",
    "reportlab",
    "fpdf",
    "tcpdf",
    "wkhtmltopdf",
    "prince",
    "weasyprint",
    "banking system",
    "core banking",
    "finacle",
    "temenos",
    "oracle flexcube",
]

# Known editing/design software (FRAUD INDICATORS)
EDITING_SOFTWARE = [
    "photoshop",
    "illustrator",
    "gimp",
    "canva",
    "figma",
    "sketch",
    "affinity",
    "inkscape",
    "corel",
    "paint.net",
    "pixlr",
    "photoscape",
    "fotor",
    "befunky",
    "snapseed",
    "krita",
    "paint shop",
    "acorn",
    "pixelmator",
]


def analyze_pdf_with_pymupdf(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Use PyMuPDF (fitz) for advanced PDF analysis.
    Detects software modifications, font inconsistencies, and structural issues.
    """
    if not PYMUPDF_AVAILABLE:
        return {"available": False, "error": "PyMuPDF not installed"}
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Extract comprehensive metadata
        metadata = doc.metadata or {}
        
        # Analyze creator/producer software
        creator = (metadata.get("creator") or "").lower()
        producer = (metadata.get("producer") or "").lower()
        
        software_analysis = _analyze_pdf_software(creator, producer)
        
        # Extract all fonts used in document
        fonts_used = set()
        font_details = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            fonts = page.get_fonts(full=True)
            
            for font in fonts:
                font_name = font[3] if len(font) > 3 else "Unknown"
                font_type = font[1] if len(font) > 1 else "Unknown"
                fonts_used.add(font_name)
                font_details.append({
                    "page": page_num + 1,
                    "name": font_name,
                    "type": font_type,
                })
        
        # Detect font inconsistencies (fraud indicator)
        font_inconsistency = len(fonts_used) > 5  # More than 5 different fonts is suspicious
        
        # Extract text with position information
        text_blocks = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_blocks.append({
                                "page": page_num + 1,
                                "text": span["text"],
                                "font": span["font"],
                                "size": span["size"],
                                "color": span["color"],
                            })
        
        # Detect text overlay (common fraud technique)
        text_overlay_detected = _detect_text_overlay(text_blocks)
        
        # Check for image manipulations
        images_analysis = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            
            for img_index, img in enumerate(images):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    images_analysis.append({
                        "page": page_num + 1,
                        "format": base_image["ext"],
                        "width": base_image["width"],
                        "height": base_image["height"],
                        "colorspace": base_image["colorspace"],
                    })
                except:
                    pass
        
        # Check for incremental updates (modifications)
        xref_count = doc.xref_length()
        has_incremental_updates = xref_count > 100  # High xref count suggests modifications
        
        doc.close()
        
        return {
            "available": True,
            "metadata": metadata,
            "software_analysis": software_analysis,
            "fonts_used": list(fonts_used),
            "font_count": len(fonts_used),
            "font_inconsistency": font_inconsistency,
            "text_blocks_count": len(text_blocks),
            "text_overlay_detected": text_overlay_detected,
            "images_count": len(images_analysis),
            "images_analysis": images_analysis[:10],  # First 10 images
            "xref_count": xref_count,
            "has_incremental_updates": has_incremental_updates,
            "page_count": len(doc),
        }
        
    except Exception as e:
        return {"available": False, "error": str(e)}


def analyze_pdf_with_pdfminer(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Use PDFMiner for deep PDF structure analysis.
    Extracts detailed metadata and detects structural anomalies.
    """
    if not PDFMINER_AVAILABLE:
        return {"available": False, "error": "PDFMiner not installed"}
    
    try:
        fp = io.BytesIO(pdf_bytes)
        parser = PDFParser(fp)
        document = PDFDocument(parser)
        
        # Extract metadata
        metadata = {}
        if document.info:
            for info in document.info:
                for key, value in info.items():
                    try:
                        if isinstance(value, bytes):
                            metadata[key] = value.decode('utf-8', errors='ignore')
                        else:
                            metadata[key] = str(value)
                    except:
                        pass
        
        # Count pages
        page_count = sum(1 for _ in PDFPage.create_pages(document))
        
        # Check if document is encrypted
        is_encrypted = document.is_extractable == False
        
        # Extract text using PDFMiner
        fp.seek(0)
        extracted_text = pdfminer_extract_text(fp)
        
        # Analyze text quality
        text_quality = _analyze_text_quality(extracted_text)
        
        return {
            "available": True,
            "metadata": metadata,
            "page_count": page_count,
            "is_encrypted": is_encrypted,
            "text_length": len(extracted_text),
            "text_quality": text_quality,
            "extracted_text_sample": extracted_text[:500],
        }
        
    except Exception as e:
        return {"available": False, "error": str(e)}


def _analyze_pdf_software(creator: str, producer: str) -> dict[str, Any]:
    """Analyze PDF creator/producer software for fraud indicators."""
    
    combined = f"{creator} {producer}".lower()
    
    # Check for editing software (FRAUD INDICATOR)
    editing_software_detected = []
    for software in EDITING_SOFTWARE:
        if software in combined:
            editing_software_detected.append(software)
    
    # Check for legitimate banking software
    legitimate_software_detected = []
    for software in LEGITIMATE_PDF_CREATORS:
        if software in combined:
            legitimate_software_detected.append(software)
    
    # Determine risk level
    if editing_software_detected:
        risk_level = "HIGH"
        reason = f"Document created/modified with editing software: {', '.join(editing_software_detected)}"
    elif not legitimate_software_detected:
        risk_level = "MEDIUM"
        reason = "Document creator/producer is unknown or non-standard"
    else:
        risk_level = "LOW"
        reason = f"Document created with legitimate software: {', '.join(legitimate_software_detected)}"
    
    return {
        "creator": creator,
        "producer": producer,
        "editing_software_detected": editing_software_detected,
        "legitimate_software_detected": legitimate_software_detected,
        "risk_level": risk_level,
        "reason": reason,
        "is_fraud_indicator": len(editing_software_detected) > 0,
    }


def _detect_text_overlay(text_blocks: list[dict[str, Any]]) -> bool:
    """
    Detect text overlay - a common fraud technique where text is placed
    on top of existing text to hide original content.
    """
    if len(text_blocks) < 10:
        return False
    
    # Group text blocks by page and position
    page_positions = {}
    for block in text_blocks:
        page = block["page"]
        if page not in page_positions:
            page_positions[page] = []
        page_positions[page].append(block)
    
    # Check for overlapping text (same position, different content)
    overlay_count = 0
    for page, blocks in page_positions.items():
        # Simple heuristic: if we have many small text blocks, it might be overlay
        small_blocks = [b for b in blocks if len(b["text"].strip()) < 5]
        if len(small_blocks) > len(blocks) * 0.3:  # More than 30% are tiny blocks
            overlay_count += 1
    
    return overlay_count >= 2  # At least 2 pages with potential overlay


def _analyze_text_quality(text: str) -> dict[str, Any]:
    """Analyze extracted text quality for fraud indicators."""
    
    if not text or len(text) < 50:
        return {"quality": "insufficient", "word_count": 0}
    
    words = text.split()
    word_count = len(words)
    
    # Check for garbled text (OCR errors or encoding issues)
    garbled_chars = sum(1 for c in text if ord(c) > 127 and c not in "£€$¥")
    garbled_percentage = (garbled_chars / len(text)) * 100 if text else 0
    
    # Check for repeated characters (fraud indicator)
    repeated_chars = len(re.findall(r'(.)\1{4,}', text))  # 5+ repeated chars
    
    # Check for numeric density (bank statements should have numbers)
    numeric_chars = sum(1 for c in text if c.isdigit())
    numeric_percentage = (numeric_chars / len(text)) * 100 if text else 0
    
    return {
        "quality": "good" if garbled_percentage < 5 else "poor",
        "word_count": word_count,
        "garbled_percentage": round(garbled_percentage, 2),
        "repeated_chars": repeated_chars,
        "numeric_percentage": round(numeric_percentage, 2),
        "has_sufficient_numbers": numeric_percentage > 5,  # Bank statements should have >5% numbers
    }


def get_comprehensive_pdf_analysis(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Combine PyMuPDF and PDFMiner analysis for comprehensive fraud detection.
    """
    pymupdf_result = analyze_pdf_with_pymupdf(pdf_bytes)
    pdfminer_result = analyze_pdf_with_pdfminer(pdf_bytes)
    
    # Combine results
    fraud_indicators = []
    risk_score = 0
    
    # Check PyMuPDF results
    if pymupdf_result.get("available"):
        software_analysis = pymupdf_result.get("software_analysis", {})
        
        if software_analysis.get("is_fraud_indicator"):
            fraud_indicators.append({
                "type": "editing_software",
                "severity": "high",
                "description": software_analysis.get("reason"),
                "evidence": software_analysis.get("editing_software_detected", []),
            })
            risk_score += 35
        
        if pymupdf_result.get("font_inconsistency"):
            fraud_indicators.append({
                "type": "font_inconsistency",
                "severity": "medium",
                "description": f"Document uses {pymupdf_result.get('font_count')} different fonts (suspicious)",
                "evidence": pymupdf_result.get("fonts_used", [])[:5],
            })
            risk_score += 15
        
        if pymupdf_result.get("text_overlay_detected"):
            fraud_indicators.append({
                "type": "text_overlay",
                "severity": "high",
                "description": "Text overlay detected - possible content manipulation",
                "evidence": ["Multiple overlapping text layers found"],
            })
            risk_score += 30
        
        if pymupdf_result.get("has_incremental_updates"):
            fraud_indicators.append({
                "type": "incremental_updates",
                "severity": "medium",
                "description": "Document has been modified after initial creation",
                "evidence": [f"XRef count: {pymupdf_result.get('xref_count')}"],
            })
            risk_score += 20
    
    # Check PDFMiner results
    if pdfminer_result.get("available"):
        text_quality = pdfminer_result.get("text_quality", {})
        
        if text_quality.get("garbled_percentage", 0) > 10:
            fraud_indicators.append({
                "type": "poor_text_quality",
                "severity": "medium",
                "description": f"Text extraction quality is poor ({text_quality.get('garbled_percentage')}% garbled)",
                "evidence": ["High percentage of unreadable characters"],
            })
            risk_score += 15
        
        if not text_quality.get("has_sufficient_numbers"):
            fraud_indicators.append({
                "type": "missing_financial_data",
                "severity": "low",
                "description": "Document lacks sufficient numeric data for a financial statement",
                "evidence": [f"Only {text_quality.get('numeric_percentage')}% numeric characters"],
            })
            risk_score += 10
    
    return {
        "pymupdf_analysis": pymupdf_result,
        "pdfminer_analysis": pdfminer_result,
        "fraud_indicators": fraud_indicators,
        "risk_score": min(100, risk_score),
        "total_indicators": len(fraud_indicators),
        "high_severity_count": sum(1 for i in fraud_indicators if i["severity"] == "high"),
        "medium_severity_count": sum(1 for i in fraud_indicators if i["severity"] == "medium"),
    }
