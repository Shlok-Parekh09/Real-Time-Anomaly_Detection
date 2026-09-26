import sys
import os
import json
import urllib.request

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from layers.ai.summary_generator import summary_generator

def test_call():
    # Construct a sample data matching what goes into the generator
    data = {
        "context": "KYC / Onboarding",
        "trust_score": 100.0,
        "recommendation": "AUTO_APPROVE",
        "findings": [],
        "documents": [
            {
                "filename": "xwd.jpg",
                "classification": "ID Card",
                "ocr_confidence": 98.0,
                "metadata": {}
            }
        ],
        "dataset_similarity": {
            "similarity_score": 0.0,
            "explanation": "No similar cases.",
            "top_similar_genuine": [],
            "top_similar_fraud": []
        },
        "evidence_graph": {"nodes": [], "edges": []},
        "timeline": []
    }
    
    prompt = summary_generator._build_prompt(data)
    print("--- Prompt ---")
    print(prompt)
    print("\n--- Calling Ollama ---")
    
    ollama_url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": summary_generator.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2500
        },
        "format": "json"
    }
    
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        ollama_url, 
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_body = response.read().decode('utf-8')
            res_data = json.loads(res_body)
            print("--- Response Keys ---")
            print(res_data.keys())
            message = res_data.get("message", {})
            print("--- Message Keys ---")
            print(message.keys())
            content = message.get("content", "")
            print("--- Content length ---")
            print(len(content))
            print("--- Content ---")
            print(repr(content))
    except Exception as e:
        print("Error during direct request:", e)

if __name__ == "__main__":
    test_call()
