import json
import os
from typing import Dict, Any

SETTINGS_FILE = "uploads/settings.json"

DEFAULT_SETTINGS = {
  "ollama_url": "http://localhost:11434",
  "ollama_model": "qwen3.5:9b",
  "ai_mode": "offline", # "offline" (Local Ollama) or "enhanced" (Gemini API)
  "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
  "gemini_model": "gemma-4-31b-it",
  "auto_approve_cases": True,
  "min_trust_threshold": 85.0,
  "baseline_similarity_threshold": 60.0,
  "max_ocr_retries": 3,
  "entity_matching_strictness": "medium", # "low", "medium", "strict"
  "ocr_language": "en",
  "ai_temperature": 0.1,
  "ai_reasoning_depth": "standard", # "standard", "deep"
  "ai_verbosity": "standard", # "concise", "standard", "detailed"
  "report_language": "en", # "en", "hi", "bilingual"
  "enable_bilingual_reports": True,
  "parallel_processing": True,
  "gpu_acceleration": True,
  "max_worker_threads": 4,
  "cache_ocr": True,
  "auto_backup": True,
  "db_retention_period_days": 90,
  "default_report_format": "pdf",
  "digital_watermark": "ANOBIS VERIFIED",
  "include_ai_reasoning": True,
  "include_audit_logs": True,
  "auto_baseline_learning": True,
  "enable_cross_doc_matching": True,
  "enable_metadata_analysis": True,
  "english_tts_voice": "",
  "hindi_tts_voice": "",
  "debug_logging": False
}

REMOVED_SETTINGS_KEYS = {"theme"}

def sanitize_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(data)
    for key in list(cleaned.keys()):
        if key in REMOVED_SETTINGS_KEYS or (key.endswith("_api_key") and key != "gemini_api_key"):
            cleaned.pop(key, None)
    return cleaned

class SettingsStore:
    def __init__(self):
        self._settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> Dict[str, Any]:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    data = sanitize_settings(data)
                    # Merge default keys in case of missing settings
                    for k, v in DEFAULT_SETTINGS.items():
                        if k not in data:
                            data[k] = v
                    self._settings = data
            except Exception as e:
                print(f"[SETTINGS] Failed to load settings.json: {e}")
        else:
            self.save(DEFAULT_SETTINGS)
        return self._settings

    def save(self, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Merge existing to preserve key values
        merged = self._settings.copy()
        merged.update(settings_dict)
        merged = sanitize_settings(merged)
        self._settings = merged
        
        # Ensure uploads folder exists
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print(f"[SETTINGS] Failed to write settings.json: {e}")
        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    @property
    def all(self) -> Dict[str, Any]:
        return self._settings

settings_store = SettingsStore()
