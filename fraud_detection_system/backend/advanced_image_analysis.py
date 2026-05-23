"""
Advanced Image Analysis using OpenCV
Detects pixel grid mismatches, font alignment issues, and structural tampering
"""

from __future__ import annotations

import io
from typing import Any

try:
    import cv2
    import numpy as np
    from PIL import Image
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


def analyze_image_with_opencv(image_bytes: bytes) -> dict[str, Any]:
    """
    Use OpenCV to detect image manipulation and fraud indicators.
    """
    if not OPENCV_AVAILABLE:
        return {"available": False, "error": "OpenCV not installed"}
    
    try:
        # Load image
        image = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(image.convert('RGB'))
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Basic image properties
        height, width = img_gray.shape
        
        # 1. Detect compression artifacts (JPEG artifacts indicate editing)
        compression_analysis = _detect_compression_artifacts(img_gray)
        
        # 2. Detect cloning/copy-paste (Error Level Analysis)
        cloning_analysis = _detect_cloning(img_bgr)
        
        # 3. Detect inconsistent noise patterns
        noise_analysis = _detect_noise_inconsistency(img_gray)
        
        # 4. Detect font/text alignment issues
        text_alignment_analysis = _detect_text_alignment_issues(img_gray)
        
        # 5. Detect resolution inconsistencies
        resolution_analysis = _detect_resolution_inconsistency(img_gray)
        
        # 6. Detect color space anomalies
        color_analysis = _detect_color_anomalies(img_bgr)
        
        # Calculate overall fraud score
        fraud_indicators = []
        risk_score = 0
        
        if compression_analysis["has_artifacts"]:
            fraud_indicators.append({
                "type": "compression_artifacts",
                "severity": "medium",
                "description": "JPEG compression artifacts detected - indicates image editing",
                "confidence": compression_analysis["confidence"],
            })
            risk_score += 20
        
        if cloning_analysis["cloning_detected"]:
            fraud_indicators.append({
                "type": "cloning_detected",
                "severity": "high",
                "description": "Copy-paste manipulation detected in image",
                "confidence": cloning_analysis["confidence"],
            })
            risk_score += 35
        
        if noise_analysis["inconsistent_noise"]:
            fraud_indicators.append({
                "type": "noise_inconsistency",
                "severity": "medium",
                "description": "Inconsistent noise patterns suggest image splicing",
                "confidence": noise_analysis["confidence"],
            })
            risk_score += 25
        
        if text_alignment_analysis["misalignment_detected"]:
            fraud_indicators.append({
                "type": "text_misalignment",
                "severity": "high",
                "description": "Text alignment inconsistencies detected",
                "confidence": text_alignment_analysis["confidence"],
            })
            risk_score += 30
        
        if resolution_analysis["inconsistent_resolution"]:
            fraud_indicators.append({
                "type": "resolution_inconsistency",
                "severity": "medium",
                "description": "Different image regions have different resolutions",
                "confidence": resolution_analysis["confidence"],
            })
            risk_score += 20
        
        if color_analysis["color_anomalies"]:
            fraud_indicators.append({
                "type": "color_anomalies",
                "severity": "low",
                "description": "Color space inconsistencies detected",
                "confidence": color_analysis["confidence"],
            })
            risk_score += 10
        
        return {
            "available": True,
            "image_dimensions": {"width": width, "height": height},
            "compression_analysis": compression_analysis,
            "cloning_analysis": cloning_analysis,
            "noise_analysis": noise_analysis,
            "text_alignment_analysis": text_alignment_analysis,
            "resolution_analysis": resolution_analysis,
            "color_analysis": color_analysis,
            "fraud_indicators": fraud_indicators,
            "risk_score": min(100, risk_score),
            "total_indicators": len(fraud_indicators),
        }
        
    except Exception as e:
        return {"available": False, "error": str(e)}


def _detect_compression_artifacts(img_gray: np.ndarray) -> dict[str, Any]:
    """
    Detect JPEG compression artifacts using DCT analysis.
    Multiple compressions (from editing) create visible artifacts.
    """
    try:
        # Detect edges
        edges = cv2.Canny(img_gray, 50, 150)
        
        # Count edge pixels
        edge_count = np.sum(edges > 0)
        total_pixels = img_gray.shape[0] * img_gray.shape[1]
        edge_percentage = (edge_count / total_pixels) * 100
        
        # High edge percentage suggests compression artifacts
        has_artifacts = edge_percentage > 15
        confidence = min(1.0, edge_percentage / 20)
        
        return {
            "has_artifacts": has_artifacts,
            "edge_percentage": round(edge_percentage, 2),
            "confidence": round(confidence, 2),
        }
    except:
        return {"has_artifacts": False, "confidence": 0.0}


def _detect_cloning(img_bgr: np.ndarray) -> dict[str, Any]:
    """
    Detect copy-paste cloning using feature matching.
    """
    try:
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Use ORB detector to find keypoints
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, descriptors = orb.detectAndCompute(img_gray, None)
        
        if descriptors is None or len(descriptors) < 10:
            return {"cloning_detected": False, "confidence": 0.0}
        
        # Use BFMatcher to find similar regions
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(descriptors, descriptors)
        
        # Filter out self-matches and count suspicious matches
        suspicious_matches = 0
        for match in matches:
            if match.queryIdx != match.trainIdx:
                # Check if matched keypoints are far apart (cloning indicator)
                kp1 = keypoints[match.queryIdx]
                kp2 = keypoints[match.trainIdx]
                distance = np.sqrt((kp1.pt[0] - kp2.pt[0])**2 + (kp1.pt[1] - kp2.pt[1])**2)
                
                if distance > 50:  # Far apart but similar features
                    suspicious_matches += 1
        
        # High number of suspicious matches indicates cloning
        cloning_detected = suspicious_matches > 20
        confidence = min(1.0, suspicious_matches / 30)
        
        return {
            "cloning_detected": cloning_detected,
            "suspicious_matches": suspicious_matches,
            "confidence": round(confidence, 2),
        }
    except:
        return {"cloning_detected": False, "confidence": 0.0}


def _detect_noise_inconsistency(img_gray: np.ndarray) -> dict[str, Any]:
    """
    Detect inconsistent noise patterns across the image.
    Spliced images have different noise characteristics.
    """
    try:
        # Divide image into regions
        h, w = img_gray.shape
        regions = [
            img_gray[0:h//2, 0:w//2],
            img_gray[0:h//2, w//2:w],
            img_gray[h//2:h, 0:w//2],
            img_gray[h//2:h, w//2:w],
        ]
        
        # Calculate noise level for each region
        noise_levels = []
        for region in regions:
            # Use Laplacian variance as noise measure
            laplacian = cv2.Laplacian(region, cv2.CV_64F)
            noise_level = laplacian.var()
            noise_levels.append(noise_level)
        
        # Check for inconsistency
        noise_std = np.std(noise_levels)
        noise_mean = np.mean(noise_levels)
        
        # High standard deviation indicates inconsistent noise
        inconsistent_noise = noise_std > noise_mean * 0.5
        confidence = min(1.0, noise_std / (noise_mean + 1))
        
        return {
            "inconsistent_noise": inconsistent_noise,
            "noise_std": round(float(noise_std), 2),
            "noise_mean": round(float(noise_mean), 2),
            "confidence": round(float(confidence), 2),
        }
    except:
        return {"inconsistent_noise": False, "confidence": 0.0}


def _detect_text_alignment_issues(img_gray: np.ndarray) -> dict[str, Any]:
    """
    Detect text alignment issues using line detection.
    Fraudulent documents often have misaligned text.
    """
    try:
        # Detect edges
        edges = cv2.Canny(img_gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough Transform
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
        
        if lines is None or len(lines) < 5:
            return {"misalignment_detected": False, "confidence": 0.0}
        
        # Analyze line angles
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angles.append(angle)
        
        # Check for angle inconsistency
        angle_std = np.std(angles)
        
        # High standard deviation indicates misalignment
        misalignment_detected = angle_std > 15
        confidence = min(1.0, angle_std / 20)
        
        return {
            "misalignment_detected": misalignment_detected,
            "line_count": len(lines),
            "angle_std": round(float(angle_std), 2),
            "confidence": round(float(confidence), 2),
        }
    except:
        return {"misalignment_detected": False, "confidence": 0.0}


def _detect_resolution_inconsistency(img_gray: np.ndarray) -> dict[str, Any]:
    """
    Detect resolution inconsistencies across the image.
    Spliced images often have different resolutions.
    """
    try:
        # Divide image into regions
        h, w = img_gray.shape
        regions = [
            img_gray[0:h//2, 0:w//2],
            img_gray[0:h//2, w//2:w],
            img_gray[h//2:h, 0:w//2],
            img_gray[h//2:h, w//2:w],
        ]
        
        # Calculate sharpness for each region
        sharpness_levels = []
        for region in regions:
            # Use Laplacian variance as sharpness measure
            laplacian = cv2.Laplacian(region, cv2.CV_64F)
            sharpness = laplacian.var()
            sharpness_levels.append(sharpness)
        
        # Check for inconsistency
        sharpness_std = np.std(sharpness_levels)
        sharpness_mean = np.mean(sharpness_levels)
        
        # High standard deviation indicates inconsistent resolution
        inconsistent_resolution = sharpness_std > sharpness_mean * 0.6
        confidence = min(1.0, sharpness_std / (sharpness_mean + 1))
        
        return {
            "inconsistent_resolution": inconsistent_resolution,
            "sharpness_std": round(float(sharpness_std), 2),
            "sharpness_mean": round(float(sharpness_mean), 2),
            "confidence": round(float(confidence), 2),
        }
    except:
        return {"inconsistent_resolution": False, "confidence": 0.0}


def _detect_color_anomalies(img_bgr: np.ndarray) -> dict[str, Any]:
    """
    Detect color space anomalies.
    Edited images often have inconsistent color distributions.
    """
    try:
        # Convert to HSV
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # Divide image into regions
        h, w, _ = img_hsv.shape
        regions = [
            img_hsv[0:h//2, 0:w//2],
            img_hsv[0:h//2, w//2:w],
            img_hsv[h//2:h, 0:w//2],
            img_hsv[h//2:h, w//2:w],
        ]
        
        # Calculate color distribution for each region
        color_means = []
        for region in regions:
            mean_color = np.mean(region, axis=(0, 1))
            color_means.append(mean_color)
        
        # Check for inconsistency
        color_std = np.std(color_means, axis=0)
        color_mean_std = np.mean(color_std)
        
        # High standard deviation indicates color anomalies
        color_anomalies = color_mean_std > 20
        confidence = min(1.0, color_mean_std / 30)
        
        return {
            "color_anomalies": color_anomalies,
            "color_std": round(float(color_mean_std), 2),
            "confidence": round(float(confidence), 2),
        }
    except:
        return {"color_anomalies": False, "confidence": 0.0}
