import sys
import os
import json
import urllib.request
import time

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from layers.ai.summary_generator import summary_generator

def test_call():
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
    print("--- Calling Ollama (No JSON constraint format) ---")
    
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
            "num_predict": 2000
        }
    }
    
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        ollama_url, 
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            res_body = response.read().decode('utf-8')
            res_data = json.loads(res_body)
            duration = time.time() - start
            print(f"--- Completed in {duration:.2f} seconds ---")
            content = res_data.get("message", {}).get("content", "")
            print("Content:")
            print(content[:800] + "...")
            parsed = summary_generator._parse_json_content(content)
            print("--- Parsed Successfully! Keys: ---")
            print(parsed.keys())
    except Exception as e:
        print("Error during direct request:", e)

if __name__ == "__main__":
    test_call()
