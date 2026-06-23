import re
import io
from typing import Dict, Any, List
from .pdf_analyzer import pdf_analyzer

class DigitalForensics:
    """
    Handles digital tampering detection for various file types.
    """
    
    def analyze(self, file_bytes: bytes, filename: str, content_type: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs digital forensic checks.
        """
        findings = []
        
        file_type_lower = (content_type or "").lower()
        is_pdf = file_type_lower == "pdf" or filename.lower().endswith(".pdf")
        is_image = file_type_lower in ["png", "jpg", "jpeg"] or filename.lower().endswith((".png", ".jpg", ".jpeg"))
        
        if is_pdf:
            findings.extend(pdf_analyzer.analyze_structure(file_bytes, metadata))
        elif is_image:
            findings.extend(self._analyze_image_forensics(file_bytes, metadata))
            
        # Common metadata checks
        findings.extend(self._check_metadata_anomalies(metadata))
        
        # OCR typo/spelling check
        extracted_text = metadata.get("extracted_text", "")
        if extracted_text:
            findings.extend(self._check_ocr_spelling_anomalies(extracted_text))
            
        return findings

    def _check_metadata_anomalies(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []
        # Normalize keys to lowercase for case-insensitive lookup
        norm_meta = {str(k).lower(): v for k, v in metadata.items()}
        
        producer = str(norm_meta.get("producer", "")).lower()
        creator = str(norm_meta.get("creator", "")).lower()
        
        suspicious_software = [
            "photoshop", "illustrator", "gimp", "canva", "figma",
            "quartz pdfcontext", "liberation", "libreoffice", "acrobat",
            "pdf2go", "ilovepdf", "pdfescape", "smallpdf", "sajan", "shlok"
        ]
        
        for software in suspicious_software:
            if software in producer or software in creator:
                anomalies.append({
                    "name": "Editing Software Signature",
                    "severity": "HIGH",
                    "description": f"Metadata contains traces of editing software or author signature: {software}",
                    "evidence": [f"Producer/Creator: {software}"]
                })
                
        # Date mismatch
        created = norm_meta.get("creationdate")
        modified = norm_meta.get("moddate")
        if created and modified and created != modified:
            anomalies.append({
                "name": "Metadata Date Mismatch",
                "severity": "MEDIUM",
                "description": "Document creation and modification dates are different, suggesting post-generation editing.",
                "evidence": [f"Created: {created}", f"Modified: {modified}"]
            })
            
        return anomalies

    def _analyze_image_forensics(self, file_bytes: bytes, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        
        # Run Error Level Analysis (ELA)
        ela_results = self._run_ela(file_bytes)
        if ela_results.get("is_tampered", False):
            findings.append({
                "name": "Image Compression Tampering (ELA)",
                "severity": "HIGH",
                "description": f"Error Level Analysis indicates pixel compression anomalies (std dev: {ela_results['std_diff']:.2f}, mean: {ela_results['mean_diff']:.2f}), suggesting local image tampering.",
                "evidence": [f"ELA Standard Deviation: {ela_results['std_diff']:.2f}"]
            })
            
        return findings

    def _run_ela(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Performs Error Level Analysis (ELA) using OpenCV to detect local JPEG compression variations.
        """
        try:
            import cv2
            import numpy as np
            from PIL import Image
            
            # Load original image
            img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
            
            # Resave to temp buffer at JPEG quality 95
            temp_buf = io.BytesIO()
            img.save(temp_buf, format='JPEG', quality=95)
            temp_buf.seek(0)
            
            # Load compressed image
            img_comp = Image.open(temp_buf)
            
            # Convert to numpy arrays
            arr_orig = np.array(img, dtype=np.float32)
            arr_comp = np.array(img_comp, dtype=np.float32)
            
            # Compute absolute pixel difference
            diff = np.abs(arr_orig - arr_comp)
            
            mean_diff = np.mean(diff)
            std_diff = np.std(diff)
            
            # Heuristic: standard deviation of compression loss is higher for spliced pixels
            is_tampered = mean_diff > 3.0 or std_diff > 4.5
            
            return {
                "mean_diff": float(mean_diff),
                "std_diff": float(std_diff),
                "is_tampered": is_tampered
            }
        except Exception as e:
            print(f"[ELA] ELA check failed: {e}")
            return {"mean_diff": 0.0, "std_diff": 0.0, "is_tampered": False}

    def _check_ocr_spelling_anomalies(self, text: str) -> List[Dict[str, Any]]:
        anomalies = []
        text_lower = text.lower()
        
        # Key template typos
        typos = {
            "satement": "Statement",
            "adhaar": "Aadhaar",
            "adhar": "Aadhaar",
            "pancard": "PAN Card",
            "unon bank": "Union Bank",
            "canara bankk": "Canara Bank"
        }
        
        for typo, correct in typos.items():
            if re.search(r'\b' + typo + r'\b', text_lower):
                anomalies.append({
                    "name": "Template Spelling Anomaly",
                    "severity": "MEDIUM",
                    "description": f"Suspicious typo '{typo}' (expected spelling '{correct}') found in document text. Official banking templates rarely contain typos.",
                    "evidence": [f"Typo detected: {typo}"]
                })
        return anomalies

digital_forensics = DigitalForensics()
