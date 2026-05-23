"""
PDF Highlighter - Add colored highlights to PDF text
Uses PyPDF2 to add annotation highlights to specific text regions
"""

from __future__ import annotations

import io
from typing import Any

try:
    from PyPDF2 import PdfReader, PdfWriter
    from PyPDF2.generic import (
        DictionaryObject,
        NumberObject,
        FloatObject,
        NameObject,
        TextStringObject,
        ArrayObject,
    )
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


def create_highlight_annotation(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: tuple[float, float, float],
    page_height: float,
) -> DictionaryObject:
    """
    Create a highlight annotation for PDF.
    
    Args:
        x1, y1: Bottom-left corner coordinates
        x2, y2: Top-right corner coordinates
        color: RGB color tuple (0-1 range)
        page_height: Height of the page for coordinate conversion
    
    Returns:
        DictionaryObject representing the highlight annotation
    """
    # Convert coordinates (PDF uses bottom-left origin)
    new_highlight = DictionaryObject()
    
    new_highlight.update({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Highlight"),
        NameObject("/Rect"): ArrayObject([
            FloatObject(x1),
            FloatObject(y1),
            FloatObject(x2),
            FloatObject(y2),
        ]),
        NameObject("/QuadPoints"): ArrayObject([
            FloatObject(x1),
            FloatObject(y2),
            FloatObject(x2),
            FloatObject(y2),
            FloatObject(x1),
            FloatObject(y1),
            FloatObject(x2),
            FloatObject(y1),
        ]),
        NameObject("/C"): ArrayObject([
            FloatObject(color[0]),
            FloatObject(color[1]),
            FloatObject(color[2]),
        ]),
        NameObject("/T"): TextStringObject("Fraud Detection System"),
        NameObject("/Contents"): TextStringObject("Potential fraud indicator"),
    })
    
    return new_highlight


def get_severity_color(severity: str) -> tuple[float, float, float]:
    """
    Get RGB color for severity level (0-1 range for PDF).
    
    Returns:
        RGB tuple in 0-1 range
    """
    if severity == "high":
        return (1.0, 0.0, 0.0)  # Red
    elif severity == "medium":
        return (1.0, 0.84, 0.0)  # Yellow/Gold
    else:
        return (0.7, 0.7, 0.7)  # Gray


def add_highlights_to_pdf(
    pdf_bytes: bytes,
    highlight_regions: list[dict[str, Any]],
) -> bytes:
    """
    Add highlight annotations to PDF based on coordinate regions.
    
    Args:
        pdf_bytes: Original PDF bytes
        highlight_regions: List of regions with bbox and severity
    
    Returns:
        Modified PDF bytes with highlights
    """
    if not PYPDF2_AVAILABLE:
        return pdf_bytes
    
    try:
        # Read the PDF
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        pdf_writer = PdfWriter()
        
        # Group regions by page
        regions_by_page = {}
        for region in highlight_regions:
            page_num = region.get("page", 1) - 1  # Convert to 0-indexed
            if page_num not in regions_by_page:
                regions_by_page[page_num] = []
            regions_by_page[page_num].append(region)
        
        # Process each page
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            
            # Get page dimensions
            page_height = float(page.mediabox.height)
            page_width = float(page.mediabox.width)
            
            # Add highlights for this page
            if page_num in regions_by_page:
                annotations = []
                
                for region in regions_by_page[page_num]:
                    bbox = region.get("bbox", {})
                    severity = region.get("severity", "low")
                    
                    # Convert percentage coordinates to PDF points
                    x1 = (bbox.get("x", 0) / 100) * page_width
                    y1_top = (bbox.get("y", 0) / 100) * page_height
                    width = (bbox.get("width", 0) / 100) * page_width
                    height = (bbox.get("height", 0) / 100) * page_height
                    
                    # PDF uses bottom-left origin, so convert y coordinate
                    y1 = page_height - y1_top - height
                    y2 = page_height - y1_top
                    x2 = x1 + width
                    
                    # Get color for severity
                    color = get_severity_color(severity)
                    
                    # Create highlight annotation
                    highlight = create_highlight_annotation(
                        x1, y1, x2, y2, color, page_height
                    )
                    
                    annotations.append(highlight)
                
                # Add annotations to page
                if annotations:
                    if "/Annots" in page:
                        # Append to existing annotations
                        existing_annots = page["/Annots"]
                        for annot in annotations:
                            existing_annots.append(annot)
                    else:
                        # Create new annotations array
                        page[NameObject("/Annots")] = ArrayObject(annotations)
            
            # Add page to writer
            pdf_writer.add_page(page)
        
        # Write to bytes
        output_stream = io.BytesIO()
        pdf_writer.write(output_stream)
        output_stream.seek(0)
        
        return output_stream.read()
        
    except Exception as e:
        print(f"Failed to add highlights to PDF: {e}")
        return pdf_bytes


def create_highlighted_pdf_preview(
    pdf_bytes: bytes,
    highlight_regions: list[dict[str, Any]],
) -> bytes:
    """
    Create a highlighted version of the PDF for preview.
    This is the main function to call from the API.
    """
    return add_highlights_to_pdf(pdf_bytes, highlight_regions)

