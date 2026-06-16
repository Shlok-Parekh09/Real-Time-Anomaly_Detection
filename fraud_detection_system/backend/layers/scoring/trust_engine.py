from models.domain import AnomalyFeature

def calculate_trust_score(anomalies: list[AnomalyFeature]) -> tuple[int, str]:
    """
    Calculates a weighted fraud probability score based on the detected anomalies.
    Returns: (score, status_string)
    """
    score = 0
    
    for anomaly in anomalies:
        if anomaly.risk_level == "Critical":
            score += 40
        elif anomaly.risk_level == "High":
            score += 25
        elif anomaly.risk_level == "Medium":
            score += 10
        elif anomaly.risk_level == "Low":
            score += 5
            
    # Cap the score at 100%
    score = min(score, 100)
    
    # Determine the status
    if score >= 50:
        status = "TAMPERED"
    elif score >= 20:
        status = "SUSPICIOUS"
    else:
        status = "TRUSTED"
        
    return score, status
