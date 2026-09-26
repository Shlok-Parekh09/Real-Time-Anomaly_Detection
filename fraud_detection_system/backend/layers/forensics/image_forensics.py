"""
Image Forensics Module
Pixel-level forensic analysis for images AND PDF pages rendered to images.
Detects:
  - Error Level Analysis (ELA): manipulated regions show brighter
  - Compression noise inconsistency
  - Copy-paste block artifacts
All analysis is local using Pillow + numpy + opencv-headless.
"""

import io
import os
import tempfile
import numpy as np
from PIL import Image, ImageChops, ImageFilter
from typing import List, Tuple, Optional
from models.domain import AnomalyFeature

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import fitz  # PyMuPDF — for rendering PDF pages as images
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


def run_image_forensics(file_path: str) -> List[AnomalyFeature]:
    """
    Main entry point: runs all image forensic checks on images or PDF pages.
    """
    anomalies = []
    images: List[Tuple[Image.Image, str]] = []  # (image, source_label)

    if file_path.lower().endswith('.pdf'):
        # Render first 3 PDF pages as images for pixel analysis
        images = _render_pdf_pages(file_path, max_pages=3)
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        try:
            img = Image.open(file_path).convert("RGB")
            images = [(img, "uploaded_image")]
        except Exception as e:
            anomalies.append(AnomalyFeature(
                type="Image Load Error",
                description=f"Could not open image for forensic analysis: {str(e)}",
                risk_level="Low"
            ))
            return anomalies

    if not images:
        return anomalies

    for img, label in images:
        # 1. Error Level Analysis
        ela_result = _error_level_analysis(img)
        if ela_result:
            anomalies.append(AnomalyFeature(
                type="ELA Tampering Detected",
                description=(
                    f"Error Level Analysis on '{label}' detected regions with significantly "
                    f"different compression levels (max deviation: {ela_result['max_deviation']:.1f}). "
                    "This indicates parts of the image were edited or pasted from another source, "
                    "as they were saved at a different compression quality than the rest."
                ),
                risk_level="High" if ela_result['max_deviation'] > 60 else "Medium"
            ))

        # 2. Compression noise analysis
        noise_result = _compression_noise_analysis(img)
        if noise_result:
            anomalies.append(AnomalyFeature(
                type="Compression Noise Inconsistency",
                description=(
                    f"Non-uniform JPEG compression noise detected in '{label}'. "
                    f"The noise variance differs by {noise_result['variance_ratio']:.1f}x between "
                    "image regions. Authentic documents have uniform noise; edited regions "
                    "show different compression artifacts than surrounding text."
                ),
                risk_level="Medium"
            ))

        # 3. Copy-paste / clone detection
        if CV2_AVAILABLE:
            clone_result = _detect_copy_paste(img)
            if clone_result:
                anomalies.append(AnomalyFeature(
                    type="Copy-Paste Artifact",
                    description=(
                        f"Detected {clone_result['match_count']} regions in '{label}' that appear "
                        "to be duplicated (copy-paste). This is a strong indicator that content was "
                        "cloned within the document to hide or replace original information."
                    ),
                    risk_level="High"
                ))

    return anomalies


def _render_pdf_pages(file_path: str, max_pages: int = 3) -> List[Tuple[Image.Image, str]]:
    """Render PDF pages as PIL images for pixel analysis."""
    if not FITZ_AVAILABLE:
        return []

    images = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]
            # Render at 150 DPI for good quality without being too large
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append((img, f"page_{page_num + 1}"))
        doc.close()
    except Exception:
        pass

    return images


def _error_level_analysis(img: Image.Image) -> Optional[dict]:
    """
    ELA: Re-save image at a known quality level, then compute the difference.
    Manipulated regions will show higher difference (brighter in the ELA image).
    """
    try:
        # Re-save at quality 90
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        resaved = Image.open(buffer).convert("RGB")

        # Compute absolute difference
        diff = ImageChops.difference(img, resaved)
        diff_array = np.array(diff, dtype=np.float64)

        # Calculate statistics
        mean_diff = np.mean(diff_array)
        max_diff = np.max(diff_array)

        # Compute standard deviation across spatial blocks
        h, w = diff_array.shape[:2]
        block_size = max(32, min(h, w) // 8)
        block_means = []

        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = diff_array[y:y+block_size, x:x+block_size]
                block_means.append(np.mean(block))

        if len(block_means) < 4:
            return None

        block_std = np.std(block_means)
        block_mean = np.mean(block_means)

        # If some blocks have significantly higher ELA than others, flag it
        # A high std relative to mean indicates non-uniform compression
        if block_std > 5.0 and max_diff > 40:
            return {"max_deviation": float(max_diff), "block_std": float(block_std)}

    except Exception:
        pass

    return None


def _compression_noise_analysis(img: Image.Image) -> Optional[dict]:
    """
    Analyzes JPEG compression noise uniformity across image quadrants.
    Authentic images have uniform noise; edited regions have different noise levels.
    """
    try:
        img_array = np.array(img.convert("L"), dtype=np.float64)
        h, w = img_array.shape

        if h < 100 or w < 100:
            return None

        # Apply high-pass filter to isolate noise
        blurred = np.array(img.convert("L").filter(ImageFilter.GaussianBlur(radius=2)), dtype=np.float64)
        noise = np.abs(img_array - blurred)

        # Divide into quadrants and compare noise levels
        mid_h, mid_w = h // 2, w // 2
        quadrants = [
            noise[:mid_h, :mid_w],       # top-left
            noise[:mid_h, mid_w:],        # top-right
            noise[mid_h:, :mid_w],        # bottom-left
            noise[mid_h:, mid_w:],        # bottom-right
        ]

        variances = [np.var(q) for q in quadrants]
        min_var = min(variances)
        max_var = max(variances)

        if min_var > 0:
            ratio = max_var / min_var
            if ratio > 3.0:  # Significant noise inconsistency
                return {"variance_ratio": ratio}

    except Exception:
        pass

    return None


def _detect_copy_paste(img: Image.Image) -> Optional[dict]:
    """
    Detects duplicated (copy-paste) regions using ORB feature matching.
    """
    if not CV2_AVAILABLE:
        return None

    try:
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

        # Resize if too large
        max_dim = 1000
        h, w = img_cv.shape
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)))

        # Detect features using ORB
        orb = cv2.ORB_create(nfeatures=1000)
        keypoints, descriptors = orb.detectAndCompute(img_cv, None)

        if descriptors is None or len(keypoints) < 10:
            return None

        # Match features against themselves
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(descriptors, descriptors, k=2)

        # Find matches that are nearby in descriptor space but far in spatial space
        clone_matches = 0
        for match_pair in matches:
            if len(match_pair) < 2:
                continue
            m, n = match_pair
            # Same keypoint — skip
            if m.queryIdx == m.trainIdx:
                continue
            # Good match in descriptor space
            if m.distance < 30:
                # Check spatial distance — cloned regions are far apart spatially
                pt1 = keypoints[m.queryIdx].pt
                pt2 = keypoints[m.trainIdx].pt
                spatial_dist = np.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
                if spatial_dist > 50:  # At least 50px apart
                    clone_matches += 1

        if clone_matches > 15:  # Threshold for reporting
            return {"match_count": clone_matches}

    except Exception:
        pass

    return None
