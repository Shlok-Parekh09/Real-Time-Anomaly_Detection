"""
Complete Forensics Engine - All checks run locally
No external API dependencies
"""
import io
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple
from PIL import Image
import numpy as np

try:
    from PyPDF2 import PdfReader
except ImportError:
    from pypdf import PdfReader


class ForensicsEngine:
    """Runs all forensic checks on documents"""
    
    def __init__(self):
        self.anomalies = []
        self.metadata = {}
        
    def analyze_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Complete PDF forensic analysis"""
        self.anomalies = []
        
        try:
            pdf_file = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_file)
            
            # Extract metadata
            self.metadata = self._extract_pdf_metadata(reader)
            
            # Extract text
            full_text = self._extract_pdf_text(reader)
            
            # Run forensic checks
            self._check_pdf_metadata_anomalies(reader)
            self._check_pdf_structure(reader)
            self._check_text_consistency(full_text)
            self._check_dates_in_text(full_text)
            self._check_financial_data(full_text)
            
            return {
                "file_name": filename,
                "file_type": "pdf",
                "metadata": self.metadata,
                "text_content": full_text[:5000],  # First 5000 chars
                "full_text": full_text,
                "anomalies": self.anomalies,
                "anomaly_count": len(self.anomalies),
                "forensic_score": self._calculate_forensic_score()
            }
            
        except Exception as e:
            self.anomalies.append({
                "type": "error",
                "severity": "high",
                "message": f"PDF analysis error: {str(e)}"
            })
            return self._error_response(filename, "pdf", str(e))
    
    def analyze_image(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Complete image forensic analysis"""
        self.anomalies = []
        
        try:
            image = Image.open(io.BytesIO(file_bytes))
            
            # Extract metadata
            self.metadata = self._extract_image_metadata(image)
            
            # Run forensic checks
            self._check_image_quality(image)
            self._check_image_compression(file_bytes, image)
            self._check_image_dimensions(image)
            
            # Try OCR text extraction
            text_content = self._simple_ocr_fallback(image)
            
            if text_content:
                self._check_text_consistency(text_content)
                self._check_dates_in_text(text_content)
                self._check_financial_data(text_content)
            
            return {
                "file_name": filename,
                "file_type": "image",
                "metadata": self.metadata,
                "text_content": text_content[:5000] if text_content else "No text extracted",
                "full_text": text_content or "",
                "anomalies": self.anomalies,
                "anomaly_count": len(self.anomalies),
                "forensic_score": self._calculate_forensic_score()
            }
            
        except Exception as e:
            self.anomalies.append({
                "type": "error",
                "severity": "high",
                "message": f"Image analysis error: {str(e)}"
            })
            return self._error_response(filename, "image", str(e))
    
    def _extract_pdf_metadata(self, reader: PdfReader) -> Dict[str, Any]:
        """Extract PDF metadata"""
        metadata = {
            "page_count": len(reader.pages),
            "creator": "",
            "producer": "",
            "created": "",
            "modified": ""
        }
        
        if reader.metadata:
            metadata["creator"] = str(reader.metadata.get('/Creator', 'Unknown'))
            metadata["producer"] = str(reader.metadata.get('/Producer', 'Unknown'))
            metadata["created"] = str(reader.metadata.get('/CreationDate', 'Unknown'))
            metadata["modified"] = str(reader.metadata.get('/ModDate', 'Unknown'))
        
        return metadata
    
    def _extract_pdf_text(self, reader: PdfReader) -> str:
        """Extract all text from PDF"""
        text_parts = []
        for page in reader.pages:
            try:
                text_parts.append(page.extract_text())
            except:
                pass
        return "\n".join(text_parts)
    
    def _extract_image_metadata(self, image: Image.Image) -> Dict[str, Any]:
        """Extract image metadata"""
        return {
            "width": image.width,
            "height": image.height,
            "format": str(image.format),
            "mode": image.mode,
            "size_kb": len(image.tobytes()) / 1024
        }
    
    def _check_pdf_metadata_anomalies(self, reader: PdfReader):
        """Check for metadata anomalies"""
        if not reader.metadata:
            self.anomalies.append({
                "type": "metadata_missing",
                "severity": "medium",
                "message": "PDF has no metadata - may indicate tampering"
            })
            return
        
        # Check for suspicious creator/producer
        creator = str(reader.metadata.get('/Creator', '')).lower()
        producer = str(reader.metadata.get('/Producer', '')).lower()
        
        suspicious_tools = ['photoshop', 'gimp', 'inkscape', 'illustrator', 'paint']
        for tool in suspicious_tools:
            if tool in creator or tool in producer:
                self.anomalies.append({
                    "type": "suspicious_creator",
                    "severity": "high",
                    "message": f"Document created with image editing software: {tool}"
                })
        
        # Check date consistency
        created = str(reader.metadata.get('/CreationDate', ''))
        modified = str(reader.metadata.get('/ModDate', ''))
        
        if created and modified:
            if modified < created:
                self.anomalies.append({
                    "type": "date_inconsistency",
                    "severity": "high",
                    "message": "Modified date is before creation date"
                })
    
    def _check_pdf_structure(self, reader: PdfReader):
        """Check PDF structure"""
        page_count = len(reader.pages)
        
        if page_count == 1:
            self.anomalies.append({
                "type": "single_page",
                "severity": "low",
                "message": "Bank statements typically have multiple pages"
            })
        
        if page_count > 50:
            self.anomalies.append({
                "type": "excessive_pages",
                "severity": "medium",
                "message": f"Unusually high page count: {page_count}"
            })
    
    def _check_text_consistency(self, text: str):
        """Check text for consistency issues"""
        if not text or len(text) < 50:
            self.anomalies.append({
                "type": "insufficient_text",
                "severity": "medium",
                "message": "Document contains very little text"
            })
            return
        
        # Check for mixed fonts/encodings (basic heuristic)
        lines = text.split('\n')
        spacing_variance = []
        
        for line in lines[:100]:  # Check first 100 lines
            if len(line) > 10:
                spaces = line.count(' ')
                spacing_variance.append(spaces / len(line))
        
        if len(spacing_variance) > 10:
            variance = np.var(spacing_variance)
            if variance > 0.05:
                self.anomalies.append({
                    "type": "formatting_inconsistency",
                    "severity": "medium",
                    "message": "Inconsistent text formatting detected"
                })
    
    def _check_dates_in_text(self, text: str):
        """Check for invalid dates"""
        # Find dates in various formats
        date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',  # DD/MM/YYYY or MM/DD/YYYY
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',    # YYYY/MM/DD
        ]
        
        found_dates = []
        for pattern in date_patterns:
            found_dates.extend(re.findall(pattern, text))
        
        for date_parts in found_dates[:50]:  # Check first 50 dates
            try:
                # Try to parse and validate
                if len(date_parts) == 3:
                    d, m, y = map(int, date_parts)
                    
                    # Check for impossible dates
                    if m > 12 or m < 1:
                        self.anomalies.append({
                            "type": "invalid_date",
                            "severity": "high",
                            "message": f"Invalid month: {m}"
                        })
                    
                    if d > 31 or d < 1:
                        self.anomalies.append({
                            "type": "invalid_date",
                            "severity": "high",
                            "message": f"Invalid day: {d}"
                        })
                    
                    # Check for future dates
                    if y > 2000:  # Assume 4-digit year
                        date_obj = datetime(y, m, d)
                        if date_obj > datetime.now():
                            self.anomalies.append({
                                "type": "future_date",
                                "severity": "high",
                                "message": f"Future date found: {d}/{m}/{y}"
                            })
            except (ValueError, Exception):
                pass
    
    def _check_financial_data(self, text: str):
        """Check financial data for anomalies"""
        # Find currency amounts
        amount_pattern = r'[\$£€¥₹]\s*[\d,]+\.?\d*|\b\d+\.\d{2}\b'
        amounts = re.findall(amount_pattern, text)
        
        if amounts:
            # Check for suspiciously round numbers
            round_count = 0
            for amount in amounts[:100]:
                clean_amount = re.sub(r'[^\d.]', '', amount)
                try:
                    value = float(clean_amount)
                    if value > 100 and value % 100 == 0:
                        round_count += 1
                except ValueError:
                    pass
            
            if round_count > len(amounts) * 0.5:
                self.anomalies.append({
                    "type": "suspicious_amounts",
                    "severity": "medium",
                    "message": f"Too many round numbers ({round_count}/{len(amounts)})"
                })
        
        # Check for negative balances
        negative_pattern = r'-\s*[\$£€¥₹]?\s*[\d,]+\.?\d*'
        negatives = re.findall(negative_pattern, text)
        
        if len(negatives) > 10:
            self.anomalies.append({
                "type": "frequent_negatives",
                "severity": "medium",
                "message": f"Frequent negative amounts ({len(negatives)} found)"
            })
    
    def _check_image_quality(self, image: Image.Image):
        """Check image quality"""
        if image.width < 800 or image.height < 600:
            self.anomalies.append({
                "type": "low_resolution",
                "severity": "medium",
                "message": f"Low resolution image: {image.width}x{image.height}"
            })
        
        if image.width > 5000 or image.height > 5000:
            self.anomalies.append({
                "type": "excessive_resolution",
                "severity": "low",
                "message": f"Unusually high resolution: {image.width}x{image.height}"
            })
    
    def _check_image_compression(self, file_bytes: bytes, image: Image.Image):
        """Check for compression artifacts"""
        file_size = len(file_bytes)
        pixel_count = image.width * image.height
        
        # Calculate bytes per pixel
        if pixel_count > 0:
            bytes_per_pixel = file_size / pixel_count
            
            if bytes_per_pixel < 0.1:
                self.anomalies.append({
                    "type": "high_compression",
                    "severity": "medium",
                    "message": "Highly compressed image - may hide alterations"
                })
            
            if bytes_per_pixel > 3:
                self.anomalies.append({
                    "type": "low_compression",
                    "severity": "low",
                    "message": "Unusually low compression for document scan"
                })
    
    def _check_image_dimensions(self, image: Image.Image):
        """Check image dimensions"""
        aspect_ratio = image.width / image.height if image.height > 0 else 0
        
        # A4 paper is roughly 1:1.4 ratio
        if aspect_ratio < 0.6 or aspect_ratio > 1.8:
            self.anomalies.append({
                "type": "unusual_aspect_ratio",
                "severity": "low",
                "message": f"Unusual aspect ratio: {aspect_ratio:.2f}"
            })
    
    def _simple_ocr_fallback(self, image: Image.Image) -> str:
        """Simple OCR fallback - returns empty string (OCR requires pytesseract)"""
        # In production, you could add pytesseract here
        # For now, return empty to avoid external dependencies
        return ""
    
    def _calculate_forensic_score(self) -> float:
        """Calculate overall forensic score (0-100, lower is more suspicious)"""
        if not self.anomalies:
            return 95.0
        
        score = 100.0
        for anomaly in self.anomalies:
            severity = anomaly.get('severity', 'low')
            if severity == 'high':
                score -= 15
            elif severity == 'medium':
                score -= 8
            else:
                score -= 3
        
        return max(0.0, min(100.0, score))
    
    def _error_response(self, filename: str, file_type: str, error: str) -> Dict[str, Any]:
        """Return error response"""
        return {
            "file_name": filename,
            "file_type": file_type,
            "metadata": {},
            "text_content": "",
            "full_text": "",
            "anomalies": self.anomalies,
            "anomaly_count": len(self.anomalies),
            "forensic_score": 0.0,
            "error": error
        }
