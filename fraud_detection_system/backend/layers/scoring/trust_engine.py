"""
Trust Engine
Calculates weighted fraud probability scores and confidence scores.
Implements the scoring methodology from ARCHITECTURE.md.
"""

from models.domain import AnomalyFeature
from typing import List, Tuple


def calculate_trust_score(anomalies: List[AnomalyFeature]) -> Tuple[int, str]:
    """
    Calculates a weighted fraud probability score based on detected anomalies.
    Uses a base-100 deduction model with capped deductions per severity tier.
    
    Returns: (fraud_probability_score 0-100, status_string)
    """
    # Start from a base trust of 100, then deduct
    base_trust = 100

    # Severity deduction values
    severity_weights = {
        "Critical": 40,
        "High": 25,
        "Medium": 10,
        "Low": 5
    }

    # Maximum total deductions per tier (prevents a flood of LOW from overwhelming)
    max_deductions = {
        "Critical": 100,  # Uncapped
        "High": 100,      # Uncapped
        "Medium": 50,     # Max 50 points from medium findings
        "Low": 25         # Max 25 points from low findings
    }

    # Calculate deductions per tier
    tier_deductions = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}

    for anomaly in anomalies:
        level = anomaly.risk_level
        if level in severity_weights:
            tier_deductions[level] += severity_weights[level]

    # Apply caps
    total_deduction = 0
    for tier, deduction in tier_deductions.items():
        capped = min(deduction, max_deductions.get(tier, deduction))
        total_deduction += capped

    trust_score = max(0, base_trust - total_deduction)

    # Convert trust_score to fraud_probability_score (inverse)
    fraud_score = 100 - trust_score

    # Determine status
    if fraud_score >= 50:
        status = "TAMPERED"
    elif fraud_score >= 20:
        status = "SUSPICIOUS"
    else:
        status = "TRUSTED"

    return fraud_score, status


def calculate_confidence_score(anomalies: List[AnomalyFeature], extracted_text: str = "") -> int:
    """
    Calculates how confident the system is in its analysis.
    Based on:
    - Amount of text successfully extracted (OCR quality proxy)
    - Number of anomaly checks that ran successfully
    - Whether errors occurred during analysis
    """
    score = 70  # Base confidence

    # Bonus for having substantial text to analyze
    text_length = len(extracted_text) if extracted_text else 0
    if text_length > 1000:
        score += 15
    elif text_length > 200:
        score += 10
    elif text_length > 0:
        score += 5

    # Bonus for having multiple anomaly checks that ran
    check_types = set(a.type for a in anomalies)
    if len(check_types) >= 3:
        score += 10
    elif len(check_types) >= 1:
        score += 5

    # Penalty for extraction errors
    error_anomalies = [a for a in anomalies if "Error" in a.type]
    score -= len(error_anomalies) * 10

    return max(10, min(100, score))


def get_recommendation(fraud_score: int, confidence: int) -> str:
    """
    Generates a recommendation based on scores.
    """
    if fraud_score < 15 and confidence > 80:
        return "AUTO_APPROVE"
    elif fraud_score >= 50:
        return "HIGH_RISK_MANUAL_REVIEW"
    elif confidence < 60:
        return "MANUAL_REVIEW"
    else:
        return "MANUAL_REVIEW"
