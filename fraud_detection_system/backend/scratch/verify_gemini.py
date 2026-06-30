import os
import sys
import json
import asyncio
import urllib.request
import urllib.error

# Add backend directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.settings_store import settings_store
from layers.ai.summary_generator import SummaryGenerator
from services.report_generator import report_generator
from core.database import SessionLocal, engine, Base
from models.database import Investigation, Document

async def verify_pipeline():
    print("=======================================")
    print("   ANOBIS GEMINI PIPELINE VERIFIER     ")
    print("=======================================\n")

    # 1. Verify Settings Persistence
    print("1. Testing settings persistence...")
    original_settings = settings_store.all.copy()
    
    test_key = "AIzaSyTestKey_12345"
    settings_store.save({
        "ai_mode": "enhanced",
        "gemini_api_key": test_key,
        "ollama_model": "gemma4:e4b"
    })
    
    loaded_settings = settings_store.load()
    if loaded_settings.get("gemini_api_key") == test_key and loaded_settings.get("ai_mode") == "enhanced":
        print("✓ Settings saved and loaded successfully!")
    else:
        print("✗ Settings persistence FAILED!")
        
    # Restore original settings
    settings_store.save(original_settings)

    # 2. Verify API Key Loading
    print("\n2. Checking API key loading...")
    env_key = os.getenv("GEMINI_API_KEY", "")
    config_key = original_settings.get("gemini_api_key", "")
    
    if env_key:
        print(f"✓ Gemini API Key loaded from Environment: {env_key[:6]}...")
    elif config_key:
        print(f"✓ Gemini API Key loaded from Settings: {config_key[:6]}...")
    else:
        print("! Warning: No active Gemini API Key detected. Enhanced mode will use fallback.")

    # 3. Test Gemini API Connectivity (if key is set)
    active_key = env_key or config_key
    if active_key:
        print("\n3. Testing Gemini API connectivity...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={active_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": "Reply with only the word: CONNECTED"}]}]
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10.0) as res:
                body = res.read().decode('utf-8')
                res_data = json.loads(body)
                reply = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"✓ Gemini API connection successful! Response: {reply}")
        except Exception as e:
            print(f"✗ Gemini API connectivity FAILED: {e}")
    else:
        print("\n3. Skipping Gemini API connectivity check (no key).")

    # 4. Test Ollama Fallback (Offline Mode)
    print("\n4. Testing Ollama connectivity & fallback...")
    url = f"{settings_store.get('ollama_url') or 'http://localhost:11434'}/api/tags"
    ollama_ready = False
    try:
        with urllib.request.urlopen(url, timeout=3.0) as res:
            if res.status == 200:
                print("✓ Local Ollama service is reachable!")
                ollama_ready = True
    except Exception as e:
        print(f"✗ Local Ollama service is unreachable: {e}")

    # 5. Test AI Summary Generation & TTS Fields
    print("\n5. Testing AI Summary Generator & TTS outputs...")
    sg = SummaryGenerator()
    dummy_data = {
        "context": "Loan Approval",
        "trust_score": 88.0,
        "recommendation": "VERIFY_ORIGINAL",
        "documents": [
            {"filename": "payslip.pdf", "classification": "Payslip", "ocr_confidence": 95.0}
        ],
        "findings": [
            {"name": "METADATA_TAMPERING", "severity": "MEDIUM", "layer_source": "FORENSIC", "description": "PDF creator signature shows Canva", "evidence": []}
        ],
        "dataset_similarity": {"similarity_score": 50.0, "is_closest_fraud": False, "explanation": "No matching templates"},
        "evidence_graph": {},
        "timeline": []
    }
    
    # Run in offline mode to verify local generation
    settings_store.save({"ai_mode": "offline"})
    print("Running Summary Generator (Offline)...")
    try:
        summary = sg.generate_summary(dummy_data)
        print("✓ Summary generated successfully!")
        
        # Verify TTS fields (English & Hindi)
        en_text = summary.get("executive_summary", "")
        hi_text = summary.get("executive_summary_hi") or summary.get("hindi_summary") or ""
        
        if en_text:
            print(f"✓ English TTS field verified: \"{en_text[:60]}...\"")
        else:
            print("✗ English TTS field is empty!")
            
        if hi_text:
            print(f"✓ Hindi TTS field verified: \"{hi_text[:60]}...\"")
        else:
            print("✗ Hindi TTS field is empty!")
            
    except Exception as e:
        print(f"✗ Summary generation failed: {e}")
        
    # Restore original settings
    settings_store.save(original_settings)
    print("\n=======================================")
    print("       VERIFICATION COMPLETE           ")
    print("=======================================")

if __name__ == "__main__":
    asyncio.run(verify_pipeline())
