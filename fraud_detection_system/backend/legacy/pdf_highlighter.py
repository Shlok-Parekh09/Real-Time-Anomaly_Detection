"""
PDF Highlighter - Add colored highlights to PDF text
Uses PyMuPDF (fitz) to draw highlight rectangles on the PDF
"""

from __future__ import annotations

import io
from typing import Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def create_highlighted_pdf_preview(
    pdf_bytes: bytes,
    highlight_regions: list[dict[str, Any]],
) -> bytes:
    """
    Add pink highlight rectangles to PDF based on coordinate regions.
    Uses PyMuPDF to draw semi-transparent rectangles over the text.
    
    Args:
        pdf_bytes: Original PDF bytes
        highlight_regions: List of regions with bbox and severity
    
    Returns:
        Modified PDF bytes with highlights
    """
    if not PYMUPDF_AVAILABLE or not highlight_regions:
        return pdf_bytes
    
    try:
        # Open PDF from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Group regions by page
        regions_by_page = {}
        for region in highlight_regions:
            page_num = region.get("page", 1) - 1  # Convert to 0-indexed
            if page_num not in regions_by_page:
                regions_by_page[page_num] = []
            regions_by_page[page_num].append(region)
        
        # Process each page
        for page_num in range(len(doc)):
            if page_num in regions_by_page:
                page = doc[page_num]
                page_width = page.rect.width
                page_height = page.rect.height
                
                for region in regions_by_page[page_num]:
                    bbox = region.get("bbox", {})
                    
                    # Convert percentage coordinates back to PDF points
                    x0 = (bbox.get("x", 0) / 100) * page_width
                    y0 = (bbox.get("y", 0) / 100) * page_height
                    width = (bbox.get("width", 0) / 100) * page_width
                    height = (bbox.get("height", 0) / 100) * page_height
                    x1 = x0 + width
                    y1 = y0 + height
                    
                    # Create a rectangle
                    rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # Pink color matching UI (#ff4d6a) -> (1.0, 0.302, 0.416)
                    # We use a highlight annotation which inherently has multiply blend mode in most viewers
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=(1.0, 0.302, 0.416))
                    annot.update()
        
        # Save to bytes
        out_pdf = doc.write(garbage=4, deflate=True)
        doc.close()
        
        return out_pdf
        
    except Exception as e:
        print(f"[HIGHLIGHTING] Failed to add highlights: {e}")
        import traceback
        traceback.print_exc()
        return pdf_bytes
