"""
Gemma4 Integration via Ollama (Local, Free, No API Keys)
Completely autonomous fraud detection using local Gemma4 model

REQUIREMENTS:
1. Install Ollama: https://ollama.com/download
2. Pull Gemma4 model: ollama pull gemma4:latest
3. Start Ollama service: ollama serve

IMPORTANT: For best accuracy, use the largest model your system can handle.
Recommended: gemma4:latest (31B if available, or largest variant)

NO API KEYS - COMPLETELY FREE AND LOCAL!
"""

from __future__ import annotations

import json
import re
from typing import Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# Local Ollama endpoint
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_CHAT_ENDPOINT = "http://localhost:11434/api/chat"


def call_gemma4_local(prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
    """
    Call Gemma4 locally via Ollama - NO API KEY REQUIRED!
    
    Requires:
    - Ollama installed and running
    - gemma4:latest model pulled
    
    Args:
        prompt: User prompt
        system_prompt: System prompt
        temperature: Temperature for generation
    
    Returns:
        Generated text response
    """
    if not REQUESTS_AVAILABLE:
        raise Exception("requests library not available")
    
    # Use chat endpoint for better system prompt support
    # IMPORTANT: Using gemma4:latest for best accuracy
    # DO NOT reduce num_predict too much - fraud detection needs detailed analysis
    payload = {
        "model": "gemma4:latest",  # Best available Gemma4 model
        "messages": [],
        "stream": False,
        "options": {
            "temperature": 0.2,  # Lower temperature for more accurate, deterministic results
            "num_predict": 4096,  # Full context for detailed fraud analysis
            "top_p": 0.9,  # Nucleus sampling for quality
            "top_k": 40,  # Top-k sampling
        }
    }
    
    # Add system prompt if provided
    if system_prompt:
        payload["messages"].append({
            "role": "system",
            "content": system_prompt
        })
    
    # Add user prompt
    payload["messages"].append({
        "role": "user",
        "content": prompt
    })
    
    try:
        print(f"[GEMMA4] Calling local Gemma4 via Ollama...")
        print(f"[GEMMA4] Using best model for accuracy (may take 2-5 minutes)...")
        print(f"[GEMMA4] Priority: Accuracy over speed")
        
        response = requests.post(
            OLLAMA_CHAT_ENDPOINT,
            json=payload,
            timeout=600  # 10 minutes timeout for thorough analysis
        )
        
        print(f"[GEMMA4] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[GEMMA4] Error response: {response.text}")
        
        response.raise_for_status()
        
        result = response.json()
        
        # Extract content from Ollama's response format
        content = result.get("message", {}).get("content", "")
        
        if not content:
            # Fallback to response field
            content = result.get("response", "")
        
        print(f"[GEMMA4] Received response: {len(content)} characters")
        
        return content
        
    except requests.exceptions.ConnectionError as e:
        print(f"[GEMMA4] Connection Error: Cannot connect to Ollama. Is it running?")
        print(f"[GEMMA4] Start Ollama with: ollama serve")
        raise Exception("Ollama not running. Start with: ollama serve") from e
    except requests.exceptions.HTTPError as e:
        print(f"[GEMMA4] HTTP Error: {e}")
        if hasattr(e, 'response'):
            print(f"[GEMMA4] Response text: {e.response.text}")
        raise
    except Exception as e:
        print(f"[GEMMA4] Error: {e}")
        raise


def analyze_document_with_gemma4(
    file_name: str,
    file_type: str,
    extracted_text: str,
    metadata: dict[str, Any],
    raw_forensic_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Use Gemma4 (local via Ollama) to perform COMPLETE fraud detection analysis.
    NO API KEY REQUIRED - COMPLETELY FREE AND LOCAL!
    
    Returns:
        Complete analysis with fraud signals, scores, descriptions, highlighting
    """
    print(f"[GEMMA4] Starting COMPLETE fraud analysis with local Gemma4")
    print(f"[GEMMA4] Prioritizing accuracy over speed")
    
    # Prepare comprehensive context - DO NOT reduce for "performance"
    # Fraud detection needs full context for accuracy
    context = {
        "document_info": {
            "file_name": file_name,
            "file_type": file_type,
            "size_bytes": metadata.get("size_bytes", 0),
            "text_length": len(extracted_text),
        },
        "metadata": {
            "pdf_revisions": metadata.get("pdf_revision_markers", 0),
            "creator": metadata.get("Creator", ""),
            "producer": metadata.get("Producer", ""),
            "creation_date": metadata.get("CreationDate", ""),
            "mod_date": metadata.get("ModDate", ""),
        },
        "forensic_data": raw_forensic_data,
        "text_sample": extracted_text[:2000] if extracted_text else "",  # Full context for accuracy
    }
    
    system_prompt = """You are an expert fraud detection AI specializing in document forensics.

Your task is to perform THOROUGH and ACCURATE fraud analysis. Take your time to analyze carefully.

Analyze for:
1. Metadata manipulation (editing software, date mismatches)
2. Financial inconsistencies (balance errors, identical amounts, round numbers)
3. Pattern anomalies (weekend transactions, statistical outliers)
4. Document integrity (missing fields, vague descriptions, templates)
5. Visual manipulation traces
6. Suspicious software signatures
7. Statistical anomalies in transactions

Return ONLY valid JSON with this EXACT structure:
{
  "risk_score": 75.0,
  "trust_score": 25.0,
  "fraud_signals": [
    {
      "id": "unique-signal-id",
      "name": "Signal Name",
      "severity": "high|medium|low",
      "summary": "Brief summary",
      "description": "Detailed explanation with specific evidence. Be thorough.",
      "evidence": ["Specific evidence 1", "Specific evidence 2", "Specific evidence 3"],
      "confidence": 0.9,
      "highlight_values": ["$1000.00", "2024-01-15"]
    }
  ],
  "ai_explanation": {
    "summary": "Comprehensive overview of findings in 2-3 sentences.",
    "likely_alteration": "Detailed explanation of what was likely altered and how.",
    "recommended_action": "accept, reject, or request_additional_documents with reasoning"
  }
}

CRITICAL RULES:
- risk_score + trust_score must equal 100
- Include 5-10 fraud signals (be thorough, not rushed)
- Each signal must have detailed, specific evidence
- highlight_values should contain ONLY specific suspicious values (amounts, dates, numbers)
- High severity = critical fraud indicators requiring immediate attention
- Medium severity = warning signs requiring investigation
- Low severity = minor inconsistencies worth noting
- Be thorough and accurate - this is fraud detection, not a speed test
- Provide detailed explanations with specific evidence
- DO NOT rush the analysis"""

    user_prompt = f"""Perform thorough fraud analysis on this document. Take your time to be accurate.

{json.dumps(context, indent=2)}

Return complete fraud analysis in JSON format."""

    try:
        response = call_gemma4_local(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2  # Lower for more accurate results
        )
        
        print(f"[GEMMA4] Received response from local Gemma4")
        
        # Extract JSON from response
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, flags=re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response, flags=re.DOTALL)
            json_str = json_match.group(0) if json_match else response
        
        result = json.loads(json_str)
        
        # Validate structure
        required_keys = ["risk_score", "trust_score", "fraud_signals", "ai_explanation"]
        if not all(key in result for key in required_keys):
            raise ValueError(f"Missing required keys. Got: {list(result.keys())}")
        
        print(f"[GEMMA4] Analysis complete: {len(result['fraud_signals'])} signals, risk={result['risk_score']}")
        
        return result
            
    except Exception as e:
        print(f"[GEMMA4] Error in fraud analysis: {e}")
        raise


def extract_highlight_coordinates_with_gemma4(
    fraud_signals: list[dict[str, Any]],
    extracted_text: str,
) -> list[str]:
    """
    Extract highlight values from Gemma4's fraud signals.
    
    Returns:
        List of specific text values to highlight
    """
    print(f"[GEMMA4] Extracting highlight values")
    
    # Extract highlight_values from fraud signals
    highlight_values = []
    
    for signal in fraud_signals:
        if signal.get("severity") in ["high", "medium"]:
            values = signal.get("highlight_values", [])
            highlight_values.extend(values)
    
    # Remove duplicates
    highlight_values = list(dict.fromkeys(highlight_values))
    
    print(f"[GEMMA4] Found {len(highlight_values)} values to highlight: {highlight_values[:10]}")
    
    return highlight_values[:20]  # Limit to 20 for performance
