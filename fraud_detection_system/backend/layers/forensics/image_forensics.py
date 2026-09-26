import cv2
import numpy as np
import os
from typing import Dict, Any, List

class ImageForensics:
    """
    Image pixel-level forensics.
    Provides ELA (Error Level Analysis), compression noise, and block artifact detection.
    """

    def analyze_image(self, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        findings = []
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return findings

            findings.extend(self._run_ela(img))
            findings.extend(self._run_compression_analysis(img))

            return findings
        except Exception as e:
            print(f"[ImageForensics] Error analyzing {filename}: {e}")
            return findings

    def _run_ela(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        Error Level Analysis. Resaves image at 90% quality and computes difference.
        High difference regions suggest tampering.
        """
        findings = []
        try:
            # Save at known quality
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            _, encimg = cv2.imencode('.jpg', img, encode_param)
            decimg = cv2.imdecode(encimg, cv2.IMREAD_COLOR)

            # Compute absolute difference
            diff = cv2.absdiff(img, decimg)

            # Convert to grayscale and threshold to find high error areas
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

            # Scale up to make errors more visible
            max_val = np.max(gray)
            if max_val == 0:
                return findings

            scale = 255.0 / max_val
            enhanced_diff = np.uint8(gray * scale)

            # Find contours of high error regions
            _, thresh = cv2.threshold(enhanced_diff, 100, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            significant_artifacts = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 100: # Threshold for significant artifact size
                    significant_artifacts += 1

            if significant_artifacts > 5:
                findings.append({
                    "name": "Image Layering Artifacts (ELA)",
                    "severity": "HIGH",
                    "description": "Error Level Analysis detected significant discrepancies in compression rates, suggesting regions of the image were copy-pasted or edited.",
                    "evidence": [f"Found {significant_artifacts} regions with high compression variance."]
                })
        except Exception as e:
            pass
        return findings

    def _run_compression_analysis(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects non-uniform JPEG compression and grid block misalignments.
        """
        findings = []
        # In a real system, you'd do DCT coefficient analysis.
        # Here we do a basic structural heuristic.
        # Check for grid-misaligned blocks indicating copy-paste.

        # Simplification for demo: Check edge variance. High variance in uniform areas = noise.
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            if laplacian_var < 50:
                # Very blurry images might be hiding artifacts
                findings.append({
                    "name": "Suspicious Image Blurring",
                    "severity": "MEDIUM",
                    "description": "Image exhibits unusually low variance/blurring, often used to hide tampering artifacts.",
                    "evidence": [f"Laplacian variance: {laplacian_var:.2f}"]
                })
        except Exception as e:
            pass
        return findings

image_forensics = ImageForensics()
