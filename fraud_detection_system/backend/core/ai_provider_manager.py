import re
import time
import json
import logging
import urllib.request
from typing import Dict, Any, Tuple
from core.config import settings, resolve_ollama_model
from core.settings_store import settings_store

logger = logging.getLogger(__name__)

class AIProviderManager:
    def __init__(self):
        self.last_latency_ms = 0
        self.last_provider = "Local Ollama"
        self.last_model = settings.OLLAMA_MODEL
        # Readiness cache: once verified, skip Ollama /api/tags calls
        self._ai_ready_cache = False
        self._cached_model = ""
        self._cached_provider = ""

    def get_active_config(self) -> Tuple[str, str, str, str]:
        """
        Returns (execution_mode, provider_name, model_name, endpoint_url)
        dynamically based on the current settings store.
        """
        ai_mode = settings_store.get("ai_mode", "offline")
        gemini_key = settings_store.get("gemini_api_key", "")
        ollama_url = settings_store.get("ollama_url") or settings.OLLAMA_BASE_URL
        ollama_model = settings_store.get("ollama_model") or settings.OLLAMA_MODEL
        # Auto-fallback to an installed model if the configured one is missing
        ollama_model = resolve_ollama_model(ollama_model, ollama_url)

        if ai_mode == "enhanced" and gemini_key:
            gemini_model = settings_store.get("gemini_model", "gemini-1.5-pro")
            return "Enhanced", "Gemini API", gemini_model, "https://generativelanguage.googleapis.com"
        else:
            return "Offline", "Local Ollama", ollama_model, ollama_url

    def invalidate_cache(self):
        """Call this when settings change (e.g. model switch) to force re-verification."""
        self._ai_ready_cache = False
        self._cached_model = ""
        self._cached_provider = ""

    def is_ai_ready(self) -> Tuple[bool, str]:
        """
        Checks if the currently configured provider is reachable and ready.
        Uses a cache so that once verified, it returns instantly.
        """
        execution_mode, provider, model, endpoint = self.get_active_config()

        # Return cached result if the provider/model haven't changed
        if self._ai_ready_cache and self._cached_model == model and self._cached_provider == provider:
            return True, ""

        if provider == "Gemini API":
            # For Gemini, configuration of the key is sufficient for ready state
            key = settings_store.get("gemini_api_key", "")
            if key:
                self._ai_ready_cache = True
                self._cached_model = model
                self._cached_provider = provider
                return True, ""
            return False, "Gemini API key is missing"
        else:
            # Check if Ollama is running and has the model
            try:
                url = f"{endpoint}/api/tags"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=0.5) as response:
                    if response.status == 200:
                        res_body = response.read().decode('utf-8')
                        res_data = json.loads(res_body)
                        models = [m.get("name") for m in res_data.get("models", [])]
                        if model in models or any(model in m for m in models):
                            self._ai_ready_cache = True
                            self._cached_model = model
                            self._cached_provider = provider
                            return True, ""
                        elif models:
                            return True, f"Model {model} not found, but Ollama has: {', '.join(models)}"
                        return False, "Ollama connected but no models are installed"
            except Exception as e:
                return False, f"Ollama connection failed: {str(e)}"
            return False, "Ollama is offline"

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 2500, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Dispatches JSON LLM generation to the resolved active provider,
        with automatic fallback from Gemini to Ollama.
        """
        execution_mode, provider, model, endpoint = self.get_active_config()
        start_time = time.time()

        if provider == "Gemini API":
            try:
                gemini_key = settings_store.get("gemini_api_key", "")
                result = self._call_gemini(system_prompt, user_prompt, gemini_key, model, temperature, timeout)
                self.last_latency_ms = int((time.time() - start_time) * 1000)
                self.last_provider = "Gemini API"
                self.last_model = model
                return result
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}. Raising exception to avoid slow Ollama fallback.")
                raise e

        # Local Ollama path (either direct config, or fallback)
        try:
            ollama_url = settings_store.get("ollama_url") or settings.OLLAMA_BASE_URL
            ollama_model = settings_store.get("ollama_model") or settings.OLLAMA_MODEL
            # Auto-fallback to an installed model if the configured one is missing
            ollama_model = resolve_ollama_model(ollama_model, ollama_url)
            result = self._call_ollama(system_prompt, user_prompt, ollama_url, ollama_model, temperature, max_tokens, timeout)
            self.last_latency_ms = int((time.time() - start_time) * 1000)
            self.last_provider = "Local Ollama"
            self.last_model = ollama_model
            return result
        except Exception as ollama_err:
            logger.error(f"Local Ollama call failed: {ollama_err}")
            raise ollama_err

    def _call_gemini(self, system_prompt: str, user_prompt: str, gemini_key: str, model_name: str, temperature: float, timeout: float) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}\n\nCRITICAL MANDATE: Output ONLY raw valid JSON. Do not include markdown formatting, backticks, or conversational text. Begin exactly with {{ and end with }}."}]
                }
            ],
            "generationConfig": {
                "temperature": temperature
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode('utf-8')
            res_data = json.loads(res_body, strict=False)
            try:
                content_str = res_data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                raise ValueError(f"Failed to parse Gemini response payload: {res_body}") from e
                
            return self._parse_json_content(content_str)

    def _call_ollama(self, system_prompt: str, user_prompt: str, ollama_url: str, ollama_model: str, temperature: float, max_tokens: int, timeout: float) -> Dict[str, Any]:
        url = f"{ollama_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "think": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": 4096
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode('utf-8')
            res_data = json.loads(res_body, strict=False)
            content_str = res_data.get("message", {}).get("content", "")
            return self._parse_json_content(content_str)

    def _parse_json_content(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```json"):
                text = "\n".join(lines[1:-1])
            else:
                text = "\n".join(lines[1:-1])
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON. Text was: {repr(text)}")
            raise e

ai_provider_manager = AIProviderManager()
