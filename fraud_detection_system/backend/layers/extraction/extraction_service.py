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
    
    def process_document(self, file_bytes: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        """
        Runs the full extraction pipeline: Conversion -> OCR/Text -> Classification -> Entity Extraction.
        """
        # 1. Conversion (if needed)
        pdf_bytes = file_bytes
        converted_to_pdf = False
        is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg'))
        is_scanned = False
        ocr_confidence = 100.0

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
            try:
                from PIL import Image
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                
                total_conf = 0.0
                word_count = 0
                
                for page in doc:
                    # Render page as image for OCR extraction
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                    img_data = Image.open(io.BytesIO(pix.tobytes("png")))
                    
                    # Get structural word and coordinate data from Tesseract
                    ocr_data = pytesseract.image_to_data(img_data, output_type=pytesseract.Output.DICT)
                    
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
        entities = entity_extractor.extract(extracted_text, classification)

        # 6. Coordinates (for forensic fields)
        coordinates = extract_forensic_field_coordinates(pdf_bytes, extracted_text)

        return {
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

    def _preprocess_image(self, pil_img) -> Any:
        """
        Applies bilateral filtering for noise reduction while maintaining sharp text edges.
        """
        try:
            import cv2
            import numpy as np
            from PIL import Image
            
            # Convert PIL image to grayscale
            open_cv_image = np.array(pil_img.convert('L'))
            
            # Apply bilateral filter (d=9, sigmaColor=75, sigmaSpace=75)
            denoised = cv2.bilateralFilter(open_cv_image, 9, 75, 75)
            
            return Image.fromarray(denoised)
        except Exception as e:
            print(f"[OCR] OpenCV preprocessing failed: {e}. Returning original.")
            return pil_img

extraction_service = ExtractionService()
