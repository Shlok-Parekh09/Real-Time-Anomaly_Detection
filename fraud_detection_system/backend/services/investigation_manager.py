import asyncio
import os
from models.domain import InvestigationResponse, AnomalyFeature
from layers.forensics.digital_forensics import validate_metadata
from layers.context.financial_validator import run_financial_analysis
from layers.scoring.trust_engine import calculate_trust_score

class InvestigationManager:
    """
    Orchestrates the asynchronous execution of various forensic layers.
    """
    
    async def process_document(self, file_path: str, filename: str) -> InvestigationResponse:
        anomalies: list[AnomalyFeature] = []
        is_pdf = file_path.lower().endswith('.pdf')
        
        # 1. Run Cryptographic & Metadata Engine (PDF only)
        if is_pdf:
            meta_anomalies = validate_metadata(file_path)
            anomalies.extend(meta_anomalies)
            
        # 2. Run Semantic & Mathematical Engine (PDF tabular extraction)
        if is_pdf:
            fin_anomalies = run_financial_analysis(file_path)
            anomalies.extend(fin_anomalies)
            
        # 3. Computer Vision & Pixel Engine (To be implemented fully later, stubbing for now)
        # image_anomalies = run_image_forensics(file_path)
        # anomalies.extend(image_anomalies)

        # Calculate Final Risk Score
        score, status = calculate_trust_score(anomalies)

        return InvestigationResponse(
            filename=filename,
            fraud_probability_score=score,
            status=status,
            anomalies=anomalies
        )
