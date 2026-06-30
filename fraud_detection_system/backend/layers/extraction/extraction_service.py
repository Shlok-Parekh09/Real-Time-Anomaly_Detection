import io
import re
from typing import Dict, Any, Optional
from .document_converter import convert_word_to_pdf, is_word_document
from .text_coordinate_extractor import extract_forensic_field_coordinates
from ..classification.document_classifier import document_classifier
from .entity_extractor import entity_extractor

try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

class ExtractionService:
    """
    Orchestrates the extraction process for a single document.
    """
    
    def process_document(self, file_bytes: bytes, filename: str, content_type: str, status_callback: Optional[Any] = None) -> Dict[str, Any]:
        """
        Runs the full extraction pipeline: Conversion -> OCR/Text -> Classification -> Entity Extraction.
        """
        import hashlib
        import json
        import os
        from core.settings_store import settings_store
        
        cache_enabled = settings_store.get("cache_ocr", True)
        cache_dir = "uploads/ocr_cache"
        cache_hash = None
        
        if cache_enabled:
            os.makedirs(cache_dir, exist_ok=True)
            hasher = hashlib.sha256()
            hasher.update(file_bytes)
            hasher.update(filename.encode("utf-8"))
            cache_hash = hasher.hexdigest()
            
            cache_json_path = os.path.join(cache_dir, f"{cache_hash}.json")
            cache_pdf_path = os.path.join(cache_dir, f"{cache_hash}.pdf")
            
            if os.path.exists(cache_json_path):
                try:
                    with open(cache_json_path, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                    
                    pdf_data = None
                    if cached_data.get("converted_to_pdf") and os.path.exists(cache_pdf_path):
                        with open(cache_pdf_path, "rb") as pf:
                            pdf_data = pf.read()
                            
                    if status_callback:
                        status_callback("Extracting Structured Entities", 0.9)
                        
                    return {
                        "extracted_text": cached_data["extracted_text"],
                        "metadata": cached_data["metadata"],
                        "classification": cached_data["classification"],
                        "entities": cached_data["entities"],
                        "coordinates": cached_data["coordinates"],
                        "converted_to_pdf": cached_data["converted_to_pdf"],
                        "pdf_bytes": pdf_data,
                        "ocr_confidence": cached_data["ocr_confidence"],
                        "is_scanned": cached_data["is_scanned"]
                    }
                except Exception as ce:
                    print(f"[CACHE] Failed to load cached OCR data: {ce}")

        # 1. Conversion (if needed)
        pdf_bytes = file_bytes
        converted_to_pdf = False
        is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg'))
        is_scanned = False
        ocr_confidence = 100.0

        if status_callback:
            status_callback("Preparing OCR Pipeline", 0.1)

        # A. Handle Word Documents
        if is_word_document(filename, file_bytes):
            try:
                pdf_bytes = convert_word_to_pdf(file_bytes, filename)
                converted_to_pdf = True
            except Exception as e:
                print(f"[EXTRACTION] Word to PDF conversion failed: {e}")

        # B. Handle Image Files (PNG, JPG, JPEG)
        elif is_image:
            is_scanned = True
            if status_callback:
                status_callback("Preprocessing Documents", 0.25)
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(file_bytes))
                
                # Check rotation via OSD
                if pytesseract:
                    try:
                        osd = pytesseract.image_to_osd(img)
                        rot = re.search(r'Rotate: (\d+)', osd)
                        if rot:
                            angle = int(rot.group(1))
                            if angle != 0:
                                img = img.rotate(-angle, expand=True)
                    except Exception as e:
                        print(f"[OCR] Rotation detection failed or not supported: {e}")
                
                # Preprocess image for better contrast/denoising
                try:
                    img = self._preprocess_image(img)
                except Exception as e:
                    print(f"[OCR] Image preprocessing failed: {e}")
                
                # Convert image to single-page PDF bytes
                pdf_buffer = io.BytesIO()
                img.save(pdf_buffer, format='PDF')
                pdf_bytes = pdf_buffer.getvalue()
                converted_to_pdf = True
            except Exception as e:
                print(f"[EXTRACTION] Image conversion to PDF failed: {e}")
                pdf_bytes = file_bytes

        # 2. Text & Metadata Extraction
        extracted_text = ""
        metadata = {}
        
        if fitz:
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                metadata = doc.metadata
                for page in doc:
                    extracted_text += page.get_text()
                doc.close()
            except Exception as e:
                print(f"[EXTRACTION] PDF text extraction failed: {e}")

        # Detect scanned PDFs (if PDF had very little or no native text layer)
        if not is_image and fitz and len(extracted_text.strip()) < 50:
            is_scanned = True

        # 3. Tesseract OCR overlay for images and scanned PDFs
        if is_scanned and pytesseract and fitz:
            if status_callback:
                status_callback("Running OCR", 0.5)
            try:
                from PIL import Image
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                
                total_conf = 0.0
                word_count = 0
                
                # Read OCR language preference
                ocr_lang = settings_store.get("ocr_language", "en")
                tess_lang = "eng"
                if ocr_lang == "hi":
                    tess_lang = "hin"
                elif ocr_lang == "both":
                    tess_lang = "eng+hin"
                
                for page in doc:
                    # Render page as image for OCR extraction
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                    img_data = Image.open(io.BytesIO(pix.tobytes("png")))
                    try:
                        img_data = self._preprocess_image(img_data)
                    except Exception as pe:
                        print(f"[OCR] Scanned PDF page pre-processing failed: {pe}")
                    
                    # Get structural word and coordinate data from Tesseract
                    ocr_data = pytesseract.image_to_data(img_data, lang=tess_lang, output_type=pytesseract.Output.DICT)
                    
                    page_w = page.rect.width
                    page_h = page.rect.height
                    img_w = img_data.width
                    img_h = img_data.height
                    
                    scale_x = page_w / img_w
                    scale_y = page_h / img_h
                    
                    for i in range(len(ocr_data['text'])):
                        text = ocr_data['text'][i].strip()
                        if not text:
                            continue
                            
                        x = ocr_data['left'][i]
                        y = ocr_data['top'][i]
                        w = ocr_data['width'][i]
                        h = ocr_data['height'][i]
                        conf = float(ocr_data['conf'][i])
                        
                        if conf != -1:
                            total_conf += conf
                            word_count += 1
                            
                        # Map coordinate position to insert invisible text
                        pt = fitz.Point(x * scale_x, (y + h) * scale_y)
                        font_sz = max(4, h * scale_y * 0.8)
                        
                        try:
                            page.insert_text(pt, text, fontsize=font_sz, render_mode=3)
                        except Exception:
                            try:
                                page.insert_text(pt, text, fontsize=font_sz)
                            except:
                                pass
                                
                # Re-extract text from searchable PDF
                extracted_text = ""
                for page in doc:
                    extracted_text += page.get_text()
                    
                # Save searchable PDF bytes
                pdf_bytes = doc.write()
                doc.close()
                converted_to_pdf = True
                
                if word_count > 0:
                    ocr_confidence = total_conf / word_count
                else:
                    ocr_confidence = 100.0
                    
            except Exception as e:
                print(f"[OCR] Scanned PDF text extraction / overlay failed: {e}")

        # 4. Document Classification
        classification = document_classifier.classify(extracted_text)

        # 5. Entity Extraction
        if status_callback:
            status_callback("Extracting Structured Entities", 0.75)
        entities = entity_extractor.extract(extracted_text, classification)

        # Multiple Extraction Passes with Validation
        max_ocr_retries = int(settings_store.get("max_ocr_retries", 3) or 0)
        if is_scanned and pytesseract and fitz and classification in ["PAN", "Aadhaar"] and max_ocr_retries > 0:
            has_id = (entities.get("pan") and entities.get("pan") != "-") if classification == "PAN" else (entities.get("aadhaar") and entities.get("aadhaar") != "-")
            if not has_id:
                if status_callback:
                    status_callback("Extracting Structured Entities (Retry Pass)", 0.85)
                print(f"[OCR Retry] Critical identifier missing/invalid for {classification}. Running second pass with adaptive thresholding and bilingual OCR...")
                try:
                    from PIL import Image
                    # Open original PDF or image bytes
                    doc_retry = fitz.open(stream=pdf_bytes, filetype="pdf")
                    retry_text = ""
                    tess_lang = "eng+hin"  # Force bilingual
                    
                    for page in doc_retry:
                        # Render at 3.0 resolution for finer details
                        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
                        img_data = Image.open(io.BytesIO(pix.tobytes("png")))
                        
                        # Apply adaptive thresholding for text sharpness
                        try:
                            import cv2
                            import numpy as np
                            open_cv_img = np.array(img_data.convert('L'))
                            blurred = cv2.GaussianBlur(open_cv_img, (5, 5), 0)
                            thresh = cv2.adaptiveThreshold(
                                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                cv2.THRESH_BINARY, 11, 2
                            )
                            img_data = Image.fromarray(thresh)
                        except Exception as pe:
                            print(f"[OCR Retry] Image thresholding failed: {pe}")
                            
                        # Run OCR string extraction
                        retry_text += pytesseract.image_to_string(img_data, lang=tess_lang)
                    
                    doc_retry.close()
                    
                    if len(retry_text.strip()) > 50:
                        retry_entities = entity_extractor.extract(retry_text, classification)
                        retry_has_id = (retry_entities.get("pan") and retry_entities.get("pan") != "-") if classification == "PAN" else (retry_entities.get("aadhaar") and retry_entities.get("aadhaar") != "-")
                        if retry_has_id:
                            print(f"[OCR Retry] Second pass succeeded in extracting {classification} identifier!")
                            extracted_text = retry_text
                            entities = retry_entities
                except Exception as re:
                    print(f"[OCR Retry] Second pass failed: {re}")

        # 6. Coordinates (for forensic fields)
        if status_callback:
            status_callback("Metadata Forensics", 0.95)
        coordinates = extract_forensic_field_coordinates(pdf_bytes, extracted_text)

        result = {
            "extracted_text": extracted_text,
            "metadata": metadata,
            "classification": classification,
            "entities": entities,
            "coordinates": coordinates,
            "converted_to_pdf": converted_to_pdf,
            "pdf_bytes": pdf_bytes if converted_to_pdf else None,
            "ocr_confidence": ocr_confidence,
            "is_scanned": is_scanned
        }

        # Save to OCR Cache
        if cache_enabled and cache_hash:
            try:
                os.makedirs(cache_dir, exist_ok=True)
                cache_json_path = os.path.join(cache_dir, f"{cache_hash}.json")
                cache_pdf_path = os.path.join(cache_dir, f"{cache_hash}.pdf")
                
                cached_data = {
                    "extracted_text": result["extracted_text"],
                    "metadata": result["metadata"],
                    "classification": result["classification"],
                    "entities": result["entities"],
                    "coordinates": result["coordinates"],
                    "converted_to_pdf": result["converted_to_pdf"],
                    "ocr_confidence": result["ocr_confidence"],
                    "is_scanned": result["is_scanned"]
                }
                
                with open(cache_json_path, "w", encoding="utf-8") as f:
                    json.dump(cached_data, f, indent=2, ensure_ascii=False)
                    
                if result["converted_to_pdf"] and result["pdf_bytes"]:
                    with open(cache_pdf_path, "wb") as pf:
                        pf.write(result["pdf_bytes"])
            except Exception as ce:
                print(f"[CACHE] Failed to save OCR data to cache: {ce}")

        return result

    def _preprocess_image(self, pil_img) -> Any:
        """
        Applies upscaling, contrast enhancement (CLAHE), and bilateral filtering for clean OCR.
        """
        try:
            import cv2
            import numpy as np
            from PIL import Image
            
            # Convert PIL image to grayscale
            img_gray = np.array(pil_img.convert('L'))
            
            # 1. Upscale if image is too small (low DPI)
            h, w = img_gray.shape[:2]
            if w < 1500:
                scale_factor = 2.0
                img_gray = cv2.resize(img_gray, (int(w * scale_factor), int(h * scale_factor)), interpolation=cv2.INTER_CUBIC)
            
            # 2. Apply CLAHE for contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrast_enhanced = clahe.apply(img_gray)
            
            # 3. Apply bilateral filter for noise reduction while keeping text edges sharp
            denoised = cv2.bilateralFilter(contrast_enhanced, 9, 75, 75)
            
            return Image.fromarray(denoised)
        except Exception as e:
            print(f"[OCR] Advanced OpenCV preprocessing failed: {e}. Returning original.")
            return pil_img

extraction_service = ExtractionService()
