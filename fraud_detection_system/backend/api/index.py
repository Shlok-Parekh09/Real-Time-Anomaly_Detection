from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
import io
from PyPDF2 import PdfReader
from PIL import Image

# Create FastAPI app
app = FastAPI(title="Fraud Detection API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Fraud Detection Backend is running!"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "features": ["pdf", "image", "openrouter_ai"],
        "message": "Backend is operational. AI analysis via OpenRouter."
    }

def extract_pdf_text(file_bytes):
    """Extract text from PDF"""
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        metadata = {
            "page_count": len(reader.pages),
            "creator": reader.metadata.get('/Creator', 'Unknown') if reader.metadata else 'Unknown',
            "producer": reader.metadata.get('/Producer', 'Unknown') if reader.metadata else 'Unknown',
            "created": str(reader.metadata.get('/CreationDate', 'Unknown')) if reader.metadata else 'Unknown',
            "modified": str(reader.metadata.get('/ModDate', 'Unknown')) if reader.metadata else 'Unknown',
        }
        
        return text.strip(), metadata
    except Exception as e:
        print(f"[PDF] Error extracting text: {e}")
        return "", {}

def extract_image_info(file_bytes):
    """Extract image information"""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "mode": image.mode,
        }
        
        return f"Image: {image.width}x{image.height} {image.format}", metadata
    except Exception as e:
        print(f"[IMAGE] Error extracting info: {e}")
        return "", {}

@app.post("/api/v1/extract-context")
async def extract_document_context(file: UploadFile = File(...)):
    """
    Extract document context for AI analysis.
    Returns metadata and text for OpenRouter AI processing.
    """
    try:
        file_name = file.filename or "uploaded-document"
        content_type = file.content_type or ""
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Determine file type
        file_lower = file_name.lower()
        if file_lower.endswith('.pdf'):
            file_type = "pdf"
            text, doc_metadata = extract_pdf_text(file_bytes)
        elif any(file_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff']):
            file_type = "image"
            text, doc_metadata = extract_image_info(file_bytes)
        elif any(file_lower.endswith(ext) for ext in ['.xlsx', '.xls', '.csv', '.tsv']):
            file_type = "excel"
            text = "Spreadsheet file uploaded"
            doc_metadata = {}
        else:
            file_type = "unknown"
            text = "Document uploaded"
            doc_metadata = {}
        
        # Build response
        return {
            "file_name": file_name,
            "file_type": file_type,
            "metadata": {
                "size_bytes": len(file_bytes),
                "content_type": content_type,
                **doc_metadata
            },
            "forensic_data": {
                "metadata_anomalies": [],
                "validation_anomalies": [],
                "text_confidence": 100.0,
            },
            "text_sample": text[:2000] if text else "No text extracted",
            "full_text": text,
            "message": "Upload successful. Ready for AI analysis."
        }
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# Export for Vercel
handler = app
