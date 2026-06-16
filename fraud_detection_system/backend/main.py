from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.investigation_manager import InvestigationManager
from models.domain import InvestigationResponse
import tempfile
import os

app = FastAPI(
    title="Offline Anomaly Detection API",
    description="Locally hosted API for strict, air-gapped forensic document analysis.",
    version="1.0.0"
)

# In a production offline environment, CORS might be strict, but we allow all for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "offline_engine_running"}

@app.post("/api/v1/investigate", response_model=InvestigationResponse)
async def investigate_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Only PDF and Image files are supported.")
        
    # Save uploaded file to a temporary location for local libraries to process
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        manager = InvestigationManager()
        # Execute the forensic pipeline
        result = await manager.process_document(temp_path, file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Forensic Engine Error: {str(e)}")
    finally:
        # Ensure cleanup of sensitive files immediately after processing
        if os.path.exists(temp_path):
            os.remove(temp_path)
