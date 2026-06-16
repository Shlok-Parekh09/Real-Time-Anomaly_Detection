"""
Complete Offline Fraud Detection Backend with Local LLM
No external API dependencies - works completely offline
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import tempfile
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our local modules
try:
    from api.forensics_engine import ForensicsEngine
    from api.local_llm import get_llm
    logger.info("[STARTUP] Local modules imported successfully")
except ImportError as e:
    logger.error(f"[STARTUP] Failed to import modules: {e}")
    raise

# Create FastAPI app
app = FastAPI(
    title="Offline Fraud Detection API with Local LLM",
    description="Complete forensic document analysis with local LLM - no external APIs",
    version="2.0.0"
)

# CORS - Allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize forensics engine
forensics_engine = ForensicsEngine()
logger.info("[STARTUP] Forensics engine initialized")

# LLM will be lazy-loaded on first request
logger.info("[STARTUP] LLM will be initialized on first analysis request")


# Response Models
class FraudSignal(BaseModel):
    id: str
    name: str
    severity: str
    summary: str
    description: str
    evidence: List[str]
    confidence: float
    highlight_values: List[str] = []


class AIExplanation(BaseModel):
    summary: str
    likely_alteration: str
    recommended_action: str


class AnalysisResponse(BaseModel):
    file_name: str
    file_type: str
    risk_score: float
    trust_score: float
    forensic_score: float
    anomaly_count: int
    fraud_signals: List[FraudSignal]
    ai_explanation: AIExplanation
    metadata: Dict[str, Any]
    analysis_method: str
    message: str


@app.get("/")
def health_check():
    return {
        "status": "running",
        "message": "Offline Fraud Detection with Local LLM",
        "features": ["pdf_forensics", "image_forensics", "local_llm", "offline_capable"],
        "version": "2.0.0"
    }


@app.get("/health")
def detailed_health():
    llm = get_llm()
    return {
        "status": "healthy",
        "forensics_engine": "active",
        "llm_status": "initialized" if llm.initialized else "fallback_mode",
        "llm_model": llm.model_name if llm.initialized else "rule_based",
        "supported_formats": ["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
        "message": "All systems operational"
    }


@app.post("/api/v1/extract-context")
async def extract_context(file: UploadFile = File(...)):
    """
    Extract forensic context from document
    Returns forensic analysis results
    """
    try:
        logger.info(f"[API] extract-context: {file.filename}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Read file
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Determine file type and run forensics
        file_lower = file.filename.lower()
        
        if file_lower.endswith('.pdf'):
            result = forensics_engine.analyze_pdf(file_bytes, file.filename)
        elif any(file_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff']):
            result = forensics_engine.analyze_image(file_bytes, file.filename)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: PDF, PNG, JPG, JPEG, WEBP, BMP, TIF, TIFF"
            )
        
        logger.info(f"[API] Forensics complete: {result['anomaly_count']} anomalies")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error in extract-context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    """
    Complete end-to-end fraud analysis
    Forensics + Local LLM analysis
    """
    try:
        logger.info(f"[API] Starting analysis: {file.filename}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Read file
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Step 1: Run forensic analysis
        file_lower = file.filename.lower()
        
        if file_lower.endswith('.pdf'):
            forensic_result = forensics_engine.analyze_pdf(file_bytes, file.filename)
        elif any(file_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff']):
            forensic_result = forensics_engine.analyze_image(file_bytes, file.filename)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: PDF, PNG, JPG, JPEG"
            )
        
        logger.info(f"[API] Forensics: score={forensic_result['forensic_score']}, anomalies={forensic_result['anomaly_count']}")
        
        # Step 2: Run LLM analysis
        llm = get_llm()
        
        context = {
            "file_name": file.filename,
            "file_type": forensic_result['file_type'],
            "metadata": forensic_result['metadata'],
            "text_content": forensic_result['text_content'],
            "full_text": forensic_result.get('full_text', '')
        }
        
        logger.info("[API] Running LLM analysis...")
        ai_result = llm.analyze_document(forensic_result, context)
        
        logger.info(f"[API] LLM complete: risk={ai_result['risk_score']}, signals={len(ai_result['fraud_signals'])}")
        
        # Step 3: Combine results
        response = AnalysisResponse(
            file_name=file.filename,
            file_type=forensic_result['file_type'],
            risk_score=ai_result['risk_score'],
            trust_score=ai_result['trust_score'],
            forensic_score=forensic_result['forensic_score'],
            anomaly_count=forensic_result['anomaly_count'],
            fraud_signals=[FraudSignal(**signal) for signal in ai_result['fraud_signals']],
            ai_explanation=AIExplanation(**ai_result['ai_explanation']),
            metadata=forensic_result['metadata'],
            analysis_method="local_llm" if llm.initialized else "rule_based",
            message="Analysis complete"
        )
        
        logger.info("[API] Analysis complete successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error in analyze: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@app.post("/api/v1/investigate")
async def investigate_document(file: UploadFile = File(...)):
    """
    Legacy endpoint - redirects to /analyze
    Maintains compatibility with old frontend
    """
    return await analyze_document(file)


if __name__ == "__main__":
    import uvicorn
    logger.info("[STARTUP] Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
