"""
Image Highlighter - Add colored highlights to images
Uses OpenCV to draw semi-transparent rectangles over text regions
"""

from __future__ import annotations

import io
from typing import Any

try:
    import cv2
    import numpy as np
    from PIL import Image
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


def get_severity_color_bgr(severity: str) -> tuple[int, int, int]:
    """
    Get BGR color for severity level (OpenCV uses BGR format).
    
    Returns:
        BGR tuple (0-255 range)
    """
    if severity == "high":
        return (0, 0, 255)  # Red (BGR)
    elif severity == "medium":
        return (0, 215, 255)  # Yellow/Gold (BGR)
    else:
        return (180, 180, 180)  # Gray (BGR)


def add_highlights_to_image(
    image_bytes: bytes,
    highlight_regions: list[dict[str, Any]],
) -> bytes:
    """
    Add highlight overlays to image based on coordinate regions.
    
    Args:
        image_bytes: Original image bytes
        highlight_regions: List of regions with bbox and severity
    
    Returns:
        Modified image bytes with highlights
    """
    if not CV2_AVAILABLE:
        return image_bytes
    
    try:
        # Read image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return image_bytes
        
        height, width = img.shape[:2]
        
        # Create overlay for highlights
        overlay = img.copy()
        
        # Draw each highlight region
        for region in highlight_regions:
            bbox = region.get("bbox", {})
            severity = region.get("severity", "low")
            
            # Convert percentage coordinates to pixels
            x = int((bbox.get("x", 0) / 100) * width)
            y = int((bbox.get("y", 0) / 100) * height)
            w = int((bbox.get("width", 0) / 100) * width)
            h = int((bbox.get("height", 0) / 100) * height)
            
            # Get color for severity
            color = get_severity_color_bgr(severity)
            
            # Draw filled rectangle on overlay
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
            
            # Optional: Add a border
            border_color = tuple(max(0, c - 50) for c in color)
            cv2.rectangle(overlay, (x, y), (x + w, y + h), border_color, 2)
        
        # Blend overlay with original image (40% opacity for highlight effect)
        alpha = 0.4
        img_highlighted = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        
        # Encode back to bytes
        success, buffer = cv2.imencode('.png', img_highlighted)
        if not success:
            return image_bytes
        
        return buffer.tobytes()
        
    except Exception as e:
        print(f"Failed to add highlights to image: {e}")
        return image_bytes


def create_highlighted_image_preview(
    image_bytes: bytes,
    highlight_regions: list[dict[str, Any]],
) -> bytes:
    """
    Create a highlighted version of the image for preview.
    This is the main function to call from the API.
    """
    return add_highlights_to_image(image_bytes, highlight_regions)

