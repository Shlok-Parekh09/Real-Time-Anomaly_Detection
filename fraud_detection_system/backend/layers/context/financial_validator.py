import pdfplumber
import re
import numpy as np
from models.domain import AnomalyFeature

def extract_monetary_values(text: str) -> list[float]:
    """Extracts formatted amounts (e.g., 1,234.50 or 500.00) from text."""
    pattern = r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b'
    matches = re.findall(pattern, text)
    return [float(m.replace(',', '')) for m in matches]

def analyze_benfords_law(amounts: list[float]) -> bool:
    """
    Applies Benford's law to the first digits of transaction amounts.
    Returns False if the distribution is highly statistically suspicious.
    """
    if len(amounts) < 20: 
        return True # Not enough statistical significance
        
    first_digits = [int(str(a).lstrip('0.')[0]) for a in amounts if a > 0]
    if not first_digits:
        return True
        
    counts = {i: 0 for i in range(1, 10)}
    for d in first_digits:
        counts[d] += 1
        
    # Benford expects '1' to appear ~30% of the time. 
    # If '1' is extremely rare (< 5%) in a large dataset, it indicates fabricated human numbers.
    percent_ones = counts[1] / len(amounts)
    if percent_ones < 0.05:
        return False
        
    return True

def analyze_round_numbers(amounts: list[float]) -> bool:
    """Checks if an unnatural amount of transactions end perfectly in .00"""
    if not amounts:
        return True
        
    round_numbers = [a for a in amounts if a % 1 == 0 or str(a).endswith('.00')]
    # If more than 40% of amounts are perfectly round, it's highly suspicious for a normal bank account
    if len(round_numbers) / len(amounts) > 0.40:
        return False
    return True

def run_financial_analysis(file_path: str) -> list[AnomalyFeature]:
    """Reads PDF tabular data and validates financial logic."""
    anomalies = []
    all_amounts = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    amounts = extract_monetary_values(text)
                    all_amounts.extend(amounts)
                    
                    # We can add structural balance math checking here in the future
                    # For now, we gather all amounts to run statistical analysis
                    
    except Exception as e:
        anomalies.append(AnomalyFeature(
            type="Data Extraction Error",
            description=f"Failed to parse tables: {str(e)}",
            risk_level="Medium"
        ))
        
    # Run Benford's Law
    if not analyze_benfords_law(all_amounts):
        anomalies.append(AnomalyFeature(
            type="Statistical Anomaly",
            description="Transaction amounts deviate significantly from Benford's Law (Natural Distribution). Flagged for potential human fabrication.",
            risk_level="Medium"
        ))
        
    # Run Round Number Check
    if not analyze_round_numbers(all_amounts):
        anomalies.append(AnomalyFeature(
            type="Round Number Anomaly",
            description="Unusually high frequency of round numbers ending in .00. Real statements typically feature varied cent values.",
            risk_level="Medium"
        ))

    return anomalies
