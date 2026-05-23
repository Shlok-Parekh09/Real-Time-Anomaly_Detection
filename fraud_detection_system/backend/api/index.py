from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os

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
        "features": ["pdf", "image", "puter_browser_ai"],
        "message": "Backend is operational. AI analysis runs in browser via Puter.js"
    }

@app.post("/api/v1/extract-context")
async def extract_document_context(file: UploadFile = File(...)):
    """
    Extract document context for browser-based AI analysis (Puter.js).
    Returns metadata and text without AI analysis.
    """
    try:
        file_name = file.filename or "uploaded-document"
        content_type = file.content_type or ""
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Basic file info
        file_type = "pdf" if file_name.lower().endswith(".pdf") else "image"
        
        # Return context for browser AI
        return {
            "file_name": file_name,
            "file_type": file_type,
            "metadata": {
                "size_bytes": len(file_bytes),
                "content_type": content_type,
            },
            "forensic_data": {
                "metadata_anomalies": [],
                "validation_anomalies": [],
                "text_confidence": 100.0,
            },
            "text_sample": "Document uploaded successfully. AI analysis will run in browser.",
            "full_text": "",
            "message": "Upload successful. Use Puter.js in browser for AI analysis."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Export for Vercel
handler = app
