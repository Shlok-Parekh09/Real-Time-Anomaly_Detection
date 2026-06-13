from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# New imports for Phase 1
from core.database import engine, Base
from api.routes import router as investigation_router
from core.config import settings

# Create new database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include new investigation-centric routes
app.include_router(investigation_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Document Fraud & Anomaly Detection API is running", "version": "1.0.0"}
