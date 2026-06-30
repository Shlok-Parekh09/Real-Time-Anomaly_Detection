import pdfplumber
import re
import numpy as np
from models.domain import AnomalyFeature

def extract_monetary_values(text: str) -> list[float]:
    """Extracts formatted amounts (e.g., 1,234.50 or 500.00) from text."""
    pattern = r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b|\b\d+\.\d{2}\b'
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


def validate_bank_statement_math(text: str) -> dict:
    """
    Validates basic math in bank statement text.
    Called by real_estate_signals.py to check for altered numbers.
    Returns dict with 'has_balance_mismatch' flag and details.
    """
    amounts = extract_monetary_values(text)
    
    if len(amounts) < 3:
        return {"has_balance_mismatch": False, "reason": "Not enough amounts to verify"}
    
    # Look for running balance patterns:
    # Try to find sequences where amounts should form running totals
    # A common pattern: amount1 - amount2 = amount3 (or +)
    mismatches = 0
    checks = 0
    
    for i in range(len(amounts) - 2):
        a, b, c = amounts[i], amounts[i+1], amounts[i+2]
        
        # Check if c = a + b or c = a - b
        if b > 0 and c > 0:
            checks += 1
            diff_add = abs((a + b) - c)
            diff_sub = abs((a - b) - c)
            diff_sub2 = abs((b - a) - c)
            
            # If none of the basic arithmetic relationships hold
            min_diff = min(diff_add, diff_sub, diff_sub2)
            if min_diff > 0.01:
                # Discrepancy detected — suspicious math/tampering
                mismatches += 1
    
    has_mismatch = mismatches > 0 and checks > 0 and (mismatches / checks) > 0.3
    
    validation_results = []
    if has_mismatch:
        validation_results.append({
            "type": "altered_bank_math",
            "severity": "high",
            "description": f"Running balances do not match calculated values (found {mismatches} mathematical mismatch(es) out of {checks} row check(s))."
        })
        
    return {
        "has_balance_mismatch": has_mismatch,
        "mismatches": mismatches,
        "checks": checks,
        "total_amounts_found": len(amounts),
        "validation_results": validation_results
    }


def validate_payslip_math(text: str) -> dict:
    """
    Validates basic math on a payslip (Gross Pay - Deductions = Net Pay).
    """
    gross = None
    deductions = None
    net = None
    
    # Extract using standard keywords and amount formats
    # Note: Using multi-stage matching or optional decimals
    gross_match = re.search(r"(?i)(?:gross|basic|earnings|total\s+earnings|gross\s+salary)[:\s\-]*([0-9,]+\.\d{2}|[0-9,]+)", text)
    ded_match = re.search(r"(?i)(?:deduction|total\s+deductions|deductions)[:\s\-]*([0-9,]+\.\d{2}|[0-9,]+)", text)
    net_match = re.search(r"(?i)(?:net|net\s+pay|take\s+home|salary\s+amount|net\s+salary)[:\s\-]*([0-9,]+\.\d{2}|[0-9,]+)", text)
    
    def parse_amount(val_str):
        if not val_str:
            return None
        val_clean = val_str.replace(",", "").strip()
        try:
            return float(val_clean)
        except ValueError:
            return None
            
    if gross_match:
        gross = parse_amount(gross_match.group(1))
    if ded_match:
        deductions = parse_amount(ded_match.group(1))
    if net_match:
        net = parse_amount(net_match.group(1))
        
    validation_results = []
    has_mismatch = False
    
    if gross is not None and deductions is not None and net is not None:
        expected_net = gross - deductions
        if abs(expected_net - net) > 2.0:
            has_mismatch = True
            validation_results.append({
                "type": "altered_payslip_math",
                "severity": "high",
                "description": f"Payslip math mismatch: Gross ({gross}) - Deductions ({deductions}) should be Net ({expected_net}), but Net is reported as {net}."
            })
            
    return {
        "has_payslip_mismatch": has_mismatch,
        "validation_results": validation_results,
        "gross": gross,
        "deductions": deductions,
        "net": net
    }
