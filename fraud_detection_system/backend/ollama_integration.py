"""
Ollama Integration for Autonomous Fraud Detection
Uses local Ollama models - no API keys required
- gemma4:31b-cloud for fraud detection analysis
- llama3 for descriptions
"""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import Any


OLLAMA_BASE_URL = "http://localhost:11434"
FRAUD_DETECTION_MODEL = "gemma4:31b-cloud"
DESCRIPTION_MODEL = "llama3"


def check_ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        request = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def check_model_available(model_name: str) -> bool:
    """Check if a specific model is available in Ollama."""
    try:
        request = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(request, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = data.get("models", [])
            return any(m.get("name", "").startswith(model_name) for m in models)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def call_ollama(model: str, prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
    """
    Call Ollama API with the specified model.
    
    Args:
        model: Model name (e.g., "gemma4:31b-cloud", "llama3")
        prompt: User prompt
        system_prompt: System prompt (optional)
        temperature: Temperature for generation (0.0-1.0)
    
    Returns:
        Generated text response
    """
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 1000,
        }
    }
    
    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("message", {}).get("content", "")
    except Exception as e:
        print(f"[OLLAMA] Error calling {model}: {e}")
        raise


def analyze_document_fraud(
    file_name: str,
    risk_score: float,
    trust_score: float,
    signals: list[dict[str, Any]],
    recovered_version: dict[str, Any],
    validation_status: str,
    extracted_text: str,
    metadata: dict[str, Any],
) -> dict[str, str]:
    """
    Analyze document for fraud using Gemma4 model.
    
    Returns:
        Dictionary with analysis results: summary, likely_alteration, recommended_action
    """
    print(f"[OLLAMA] Starting fraud analysis with {FRAUD_DETECTION_MODEL}")
    
    # Check if Ollama is available
    if not check_ollama_available():
        print("[OLLAMA] Ollama not available, using fallback intelligent analysis")
        raise Exception("Ollama not available")
    
    # Check if model is available
    if not check_model_available(FRAUD_DETECTION_MODEL):
        print(f"[OLLAMA] Model {FRAUD_DETECTION_MODEL} not available")
        raise Exception(f"Model {FRAUD_DETECTION_MODEL} not available")
    
    # Prepare context for analysis
    context = {
        "document_info": {
            "file_name": file_name,
            "risk_score": risk_score,
            "trust_score": trust_score,
            "file_type": metadata.get("file_type", "unknown"),
        },
        "fraud_signals": [
            {
                "name": s.get("name"),
                "severity": s.get("severity"),
                "summary": s.get("summary"),
                "confidence": s.get("confidence", 0.75),
            }
            for s in signals[:10]
        ],
        "recovery_info": {
            "previous_version_found": recovered_version.get("available", False),
            "summary": recovered_version.get("summary", ""),
            "changes_detected": len(recovered_version.get("changes", [])),
        },
        "validation": {
            "status": validation_status,
            "text_length": len(extracted_text),
        }
    }
    
    system_prompt = """You are an expert document forensics analyst specializing in fraud detection for financial documents, bank statements, payslips, and landlord verification documents.

Your task is to analyze the forensic signals and provide a concise fraud assessment.

Respond ONLY with a JSON object containing these exact keys:
{
  "summary": "Brief 2-3 sentence overview of the fraud analysis",
  "likely_alteration": "Specific description of what was likely altered or fabricated",
  "recommended_action": "Clear recommendation for the underwriter (accept/reject/request additional documents)"
}

Focus on:
- Real estate fraud patterns (fake payslips, altered bank statements, fabricated landlord documents)
- Financial manipulation (altered amounts, missing transactions, balance mismatches)
- Document authenticity (metadata inconsistencies, editing software traces, missing fields)
- Risk assessment based on severity and confidence of signals"""

    user_prompt = f"""Analyze this document for fraud:

{json.dumps(context, indent=2)}

Provide your analysis in JSON format."""

    try:
        response = call_ollama(
            model=FRAUD_DETECTION_MODEL,
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        print(f"[OLLAMA] Received response from {FRAUD_DETECTION_MODEL}")
        
        # Extract JSON from response
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, flags=re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response, flags=re.DOTALL)
            json_str = json_match.group(0) if json_match else response
        
        result = json.loads(json_str)
        
        # Validate required keys
        required_keys = ["summary", "likely_alteration", "recommended_action"]
        if all(key in result for key in required_keys):
            print(f"[OLLAMA] Successfully analyzed document")
            return {
                "summary": result["summary"],
                "likely_alteration": result["likely_alteration"],
                "recommended_action": result["recommended_action"],
                "limitations": "Analysis performed by local AI model. Manual review recommended for high-risk cases.",
                "generated_by": f"ollama_{FRAUD_DETECTION_MODEL}",
            }
        else:
            raise ValueError("Missing required keys in response")
            
    except Exception as e:
        print(f"[OLLAMA] Error in fraud analysis: {e}")
        raise


def generate_signal_description(
    signal: dict[str, Any],
    file_name: str,
) -> str:
    """
    Generate detailed description for a fraud signal using Llama model.
    
    Args:
        signal: Fraud signal dictionary
        file_name: Name of the document
    
    Returns:
        Enhanced description string
    """
    print(f"[OLLAMA] Generating description with {DESCRIPTION_MODEL}")
    
    # Check if Ollama is available
    if not check_ollama_available():
        print("[OLLAMA] Ollama not available for description generation")
        raise Exception("Ollama not available")
    
    # Check if model is available
    if not check_model_available(DESCRIPTION_MODEL):
        print(f"[OLLAMA] Model {DESCRIPTION_MODEL} not available")
        raise Exception(f"Model {DESCRIPTION_MODEL} not available")
    
    system_prompt = """You are a document forensics expert. Generate a clear, concise description (2-3 sentences) explaining why this fraud signal is important and what it indicates about the document's authenticity.

Focus on:
- What the signal means in plain language
- Why it's suspicious
- What it suggests about document manipulation

Keep it professional and actionable for underwriters."""

    user_prompt = f"""Signal: {signal.get('name')}
Severity: {signal.get('severity')}
Summary: {signal.get('summary')}
Evidence: {signal.get('evidence', [])[:3]}
Document: {file_name}

Generate a clear description of this fraud signal."""

    try:
        response = call_ollama(
            model=DESCRIPTION_MODEL,
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.4
        )
        
        # Clean up response (remove quotes, extra whitespace)
        description = response.strip().strip('"').strip("'")
        
        print(f"[OLLAMA] Generated description: {description[:100]}...")
        
        return description
        
    except Exception as e:
        print(f"[OLLAMA] Error generating description: {e}")
        raise


def batch_generate_descriptions(
    signals: list[dict[str, Any]],
    file_name: str,
    max_signals: int = 5,
) -> list[dict[str, Any]]:
    """
    Generate descriptions for multiple signals (batch processing).
    
    Args:
        signals: List of fraud signals
        file_name: Document name
        max_signals: Maximum number of signals to process
    
    Returns:
        List of signals with enhanced descriptions
    """
    enriched_signals = []
    
    for i, signal in enumerate(signals[:max_signals]):
        enriched = dict(signal)
        
        try:
            description = generate_signal_description(signal, file_name)
            if description and len(description) > 20:
                enriched["description"] = description
        except Exception as e:
            print(f"[OLLAMA] Failed to generate description for signal {i+1}: {e}")
            # Keep original description
        
        enriched_signals.append(enriched)
    
    # Add remaining signals without enhancement
    enriched_signals.extend(signals[max_signals:])
    
    return enriched_signals
