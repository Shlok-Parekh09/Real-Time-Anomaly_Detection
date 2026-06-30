import os
import sys
import shutil

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, engine, Base
from core.settings_store import settings_store
from models.database import Investigation, Document
from services.investigation_manager import investigation_manager

def run_gemini_validation():
    print("=== Transitioning to Gemini Enhanced Mode ===")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set!")
        return

    # Update settings to enhanced mode using Gemini
    settings_store.save({
        "ai_mode": "enhanced",
        "gemini_api_key": gemini_key,
        "ollama_url": "http://localhost:11434",
        "ollama_model": "gemma4:e4b"
    })
    print(f"Settings successfully updated. Mode: {settings_store.get('ai_mode')}")

    # Rebuild database tables to ensure clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("\n=== Step 1: Creating Test Case ===")
        # Find test file
        test_file_path = os.path.abspath("../dataset/testing/fraud_cases/xwd.jpg")
        if not os.path.exists(test_file_path):
            print(f"Error: Test file not found at {test_file_path}")
            return
            
        print(f"Found test file: {test_file_path}")

        investigation = Investigation(
            context="KYC / Onboarding",
            title="Gemini Enhanced Validation Case - Twitterpreet Singh",
            status="PENDING",
            progress=0,
            current_stage="CREATED"
        )
        db.add(investigation)
        db.commit()
        db.refresh(investigation)
        print(f"Created Investigation ID: {investigation.id}")

        # Setup upload workspace directories
        from core.config import settings
        case_dir = os.path.join(settings.UPLOAD_DIR, str(investigation.id))
        os.makedirs(case_dir, exist_ok=True)
        
        dest_path = os.path.join(case_dir, "xwd.jpg")
        shutil.copy(test_file_path, dest_path)
        print(f"Copied test document to uploads workspace: {dest_path}")

        # Register document
        document = Document(
            investigation_id=investigation.id,
            filename="xwd.jpg",
            file_path=dest_path,
            classification="UNKNOWN",
            ocr_text=""
        )
        db.add(document)
        db.commit()

        print("\n=== Step 2: Running Asynchronous Pipeline (Synchronously for test) ===")
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(investigation_manager.run_analysis(investigation.id))

        db.refresh(investigation)
        print(f"Pipeline Execution Status: {investigation.status}")
        print(f"Current Stage: {investigation.current_stage}")
        print(f"Calculated Trust Score: {investigation.trust_score}")
        print(f"Auditor Recommendation: {investigation.recommendation}")

        print("\n=== Step 3: Verifying Forensic Findings ===")
        print(f"Total findings flagged: {len(investigation.findings)}")
        for f in investigation.findings:
            print(f"- [{f.layer_source}] ({f.severity}) {f.title}: {f.description}")

        print("\n=== Step 4: Checking Gemini Summary Output ===")
        print("English Summary:")
        print(investigation.summary_english)
        print("\nHindi Summary:")
        print(investigation.summary_hindi)
        print("\nReviewer Notes:")
        print(investigation.reviewer_notes)

        print("\n=== Step 5: Generating PDF Report ===")
        from services.report_generator import report_generator
        pdf_path = report_generator.generate_pdf_report(investigation.id)
        print(f"PDF report successfully saved to disk: {pdf_path}")
        print(f"File Size: {os.path.getsize(pdf_path)} bytes")
        
        print("\n=== E2E Gemini Validation Completed Successfully! ===")

    finally:
        db.close()

if __name__ == "__main__":
    run_gemini_validation()
