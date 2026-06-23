"""
Anobis E2E Validation Script
Runs a full offline pipeline check on a sample file from the organized dataset
"""

import os
import sys
import asyncio
from datetime import datetime

# Setup paths to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal, engine, Base
from models.database import Investigation, Document, Finding, Evidence
from services.investigation_manager import investigation_manager
from services.report_generator import report_generator
from layers.ai.summary_generator import summary_generator

async def run_validation():
    # Clean up outdated local DB to force schema rebuild
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fraud_investigations.db"))
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("Deleted outdated SQLite database to force schema rebuild.")
        except Exception as e:
            print(f"Database reset warning: {e}")

    # Make sure tables are created
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("=== Step 1: Creating Test Case ===")
        # Scenario: Identity & Image tampering check (using testing/fraud_cases/xwd.jpg)
        test_file_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../../dataset/testing/fraud_cases/xwd.jpg"
        ))
        
        if not os.path.exists(test_file_path):
            print(f"ERROR: Sample test document not found at {test_file_path}")
            return
            
        print(f"Found test file: {test_file_path}")
        
        # Create Investigation in DB
        investigation = Investigation(
            context="KYC / Onboarding",
            title="E2E Validation Test Case - Twitterpreet Singh",
            status="PENDING",
            progress=0,
            current_stage="CREATED"
        )
        db.add(investigation)
        db.commit()
        db.refresh(investigation)
        print(f"Created Investigation ID: {investigation.id}")
        
        # Copy file to uploads folder or use directly
        upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads", investigation.id))
        os.makedirs(upload_dir, exist_ok=True)
        dest_path = os.path.join(upload_dir, "xwd.jpg")
        
        import shutil
        shutil.copy(test_file_path, dest_path)
        print(f"Copied test document to uploads workspace: {dest_path}")
        
        # Register Document in DB
        document = Document(
            investigation_id=investigation.id,
            filename="xwd.jpg",
            file_type="jpg",
            storage_path=dest_path
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        print("\n=== Step 2: Running Asynchronous Pipeline (Synchronously for test) ===")
        await investigation_manager.run_analysis(investigation.id)
        
        # Fetch updated investigation details
        db.refresh(investigation)
        print(f"Pipeline Execution Status: {investigation.status}")
        print(f"Current Stage: {investigation.current_stage}")
        print(f"Calculated Trust Score: {investigation.trust_score}")
        print(f"Calculated Confidence Score: {investigation.confidence_score}")
        print(f"Auditor Recommendation: {investigation.recommendation}")
        
        print("\n=== Step 3: Verifying Forensic Findings ===")
        findings = db.query(Finding).filter(Finding.investigation_id == investigation.id).all()
        print(f"Total findings flagged: {len(findings)}")
        for f in findings:
            print(f"- [{f.severity}] [{f.layer_source}] {f.name}: {f.description}")
            for ev in f.evidence_items:
                print(f"  * Evidence: Page {ev.page_number} in {ev.document.filename} -> {ev.description}")
                if ev.extracted_text:
                    print(f"    Text matched: \"{ev.extracted_text}\"")

        print("\n=== Step 4: Checking AI Summary Output ===")
        summary = investigation.ai_summary_json or {}
        print("English Summary:")
        print(summary.get("executive_summary", "None"))
        print("\nHindi Summary:")
        print(summary.get("executive_summary_hi") or summary.get("hindi_summary") or "None")
        print("\nReviewer Notes:")
        print(summary.get("reviewer_notes", "None"))

        print("\n=== Step 5: Generating PDF Report ===")
        pdf_bytes = report_generator.generate_pdf_report(investigation)
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"Anobis_Report_{investigation.id}.pdf"))
        with open(report_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"PDF report successfully saved to disk: {report_path}")
        print(f"File Size: {len(pdf_bytes)} bytes")
        
        print("\n=== E2E Validation Completed Successfully! ===")
        
    except Exception as e:
        print(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_validation())
