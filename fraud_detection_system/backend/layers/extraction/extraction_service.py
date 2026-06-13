import io
from typing import Dict, Any, Optional
from .document_converter import convert_word_to_pdf, is_word_document
from .text_coordinate_extractor import extract_forensic_field_coordinates
from ..classification.document_classifier import document_classifier
from .entity_extractor import entity_extractor

try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None

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
        
        if is_word_document(filename, file_bytes):
            try:
                pdf_bytes = convert_word_to_pdf(file_bytes, filename)
                converted_to_pdf = True
            except Exception as e:
                print(f"[EXTRACTION] Word to PDF conversion failed: {e}")

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

        # 3. Document Classification
        classification = document_classifier.classify(extracted_text)

        # 4. Entity Extraction
        entities = entity_extractor.extract(extracted_text, classification)

        # 5. Coordinates (for forensic fields)
        coordinates = extract_forensic_field_coordinates(pdf_bytes, extracted_text)

        return {
            "extracted_text": extracted_text,
            "metadata": metadata,
            "classification": classification,
            "entities": entities,
            "coordinates": coordinates,
            "converted_to_pdf": converted_to_pdf,
            "pdf_bytes": pdf_bytes if converted_to_pdf else None
        }

extraction_service = ExtractionService()
