"""
AI Summary Generator
Generates human-readable summaries of forensic analysis results.
Supports:
  1. Ollama (local LLM — free, no API key)
  2. Hugging Face transformers (local model)
  3. Deterministic template fallback (always works)
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    Generates human-readable summaries of investigations using AI.
    Tries local LLM (Ollama) first, then falls back to smart templates.
    """

    SYSTEM_PROMPT = """You are a professional Banking Forensic Auditor. 
Your task is to summarize document investigation findings for underwriters.

STRICT RULES:
1. Only use the PROVIDED Findings and Scores below.
2. NEVER invent new findings or fraud explanations.
3. NEVER mention entities or documents not in the input.
4. If information is missing, explicitly say 'Data not available'.
5. Be concise and objective.
6. Do NOT decide if something is fraud; explain WHY it was flagged.

OUTPUT FORMAT (JSON only, no markdown, no code blocks):
{
  "executive_summary": "English high-level summary of the forensic analysis",
  "hindi_summary": "Hindi translation of the executive summary",
  "reviewer_notes": "Specific actionable notes for the human reviewer"
}"""

    def __init__(self):
        self._ollama_available = None  # Lazy check

    def generate_summary(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates summary generation. Tries LLMs first, falls back to templates.
        """
        # Try Ollama (local, free)
        if self._check_ollama():
            try:
                result = self._call_ollama(investigation_data)
                if result:
                    logger.info("[AI] Summary generated via Ollama (local LLM)")
                    return result
            except Exception as e:
                logger.warning(f"[AI] Ollama call failed: {e}")

        # Try Hugging Face transformers (local model)
        try:
            result = self._call_transformers(investigation_data)
            if result:
                logger.info("[AI] Summary generated via local transformers model")
                return result
        except Exception as e:
            logger.warning(f"[AI] Transformers call failed: {e}")

        # Fallback: deterministic template (always works)
        logger.info("[AI] Using template-based summary (no LLM available)")
        return self._generate_template_summary(investigation_data)

    def _check_ollama(self) -> bool:
        """Check if Ollama is running locally."""
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            self._ollama_available = response.status_code == 200
        except Exception:
            try:
                import urllib.request
                req = urllib.request.Request("http://localhost:11434/api/tags")
                response = urllib.request.urlopen(req, timeout=2)
                self._ollama_available = response.status == 200
            except Exception:
                self._ollama_available = False

        if self._ollama_available:
            logger.info("[AI] Ollama detected at localhost:11434")
        return self._ollama_available

    def _call_ollama(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call Ollama's local API for summary generation."""
        prompt = self._build_prompt(data)

        payload = {
            "model": "",
            "prompt": f"{self.SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 500
            }
        }

        # First, query which models are actually installed
        models_to_try = []
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags")
            response = urllib.request.urlopen(req, timeout=3)
            tags_data = json.loads(response.read().decode())
            installed = [m["name"] for m in tags_data.get("models", [])]
            if installed:
                models_to_try = installed
                logger.info(f"[AI] Ollama installed models: {installed}")
        except Exception:
            pass

        # Fall back to common model names if we couldn't query tags
        if not models_to_try:
            models_to_try = [
                "gemma3:1b", "gemma3:4b", "gemma2:2b", "gemma2",
                "llama3.2:1b", "llama3.2", "llama3.1", "llama3",
                "mistral", "phi3", "qwen2", "tinyllama"
            ]

        for model in models_to_try:
            payload["model"] = model
            try:
                import urllib.request
                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                response = urllib.request.urlopen(req, timeout=60)
                result = json.loads(response.read().decode())

                if "response" in result:
                    logger.info(f"[AI] Ollama model '{model}' responded successfully")
                    return self._parse_llm_response(result["response"])
            except Exception as e:
                error_str = str(e).lower()
                if "not found" in error_str or "404" in error_str:
                    continue  # Try next model
                logger.warning(f"[AI] Ollama model '{model}' failed: {e}")
                continue

        return None


    def _call_transformers(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use Hugging Face transformers for local inference."""
        try:
            from transformers import pipeline
            
            prompt = self._build_prompt(data)
            full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}\n\nJSON Response:"

            # Use a small text-generation model
            generator = pipeline(
                "text-generation",
                model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                device_map="auto",
                max_new_tokens=400,
                temperature=0.3,
                do_sample=True
            )

            result = generator(full_prompt)
            if result and len(result) > 0:
                generated_text = result[0].get("generated_text", "")
                # Extract the part after our prompt
                response_text = generated_text[len(full_prompt):].strip()
                return self._parse_llm_response(response_text)

        except ImportError:
            logger.debug("[AI] transformers not available")
        except Exception as e:
            logger.debug(f"[AI] transformers inference failed: {e}")

        return None

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """Serialize investigation results into a structured prompt."""
        anomalies = data.get("anomalies", [])
        
        findings_str = "\n".join([
            f"- [{a.get('risk_level', a.get('severity', 'Unknown'))}] {a.get('type', a.get('name', 'Unknown'))}: {a.get('description', '')}"
            for a in anomalies
        ]) if anomalies else "No anomalies detected."

        prompt = f"""DOCUMENT: {data.get('filename', 'Unknown')}
FRAUD PROBABILITY SCORE: {data.get('fraud_probability_score', 'N/A')}/100
STATUS: {data.get('status', 'N/A')}

DETECTED ANOMALIES ({len(anomalies)} total):
{findings_str}

Based ONLY on the above findings, provide the analysis summary in the requested JSON format."""
        return prompt

    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response text into structured dict."""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        json_match = re.search(r'\{[^{}]*"executive_summary"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Last resort: extract key pieces from the text
        return {
            "executive_summary": response_text[:500].strip(),
            "hindi_summary": "AI-जनित सारांश उपलब्ध है लेकिन प्रारूपण विफल रहा।",
            "reviewer_notes": "LLM response could not be parsed into structured format. Raw output available."
        }

    def _generate_template_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Smart deterministic fallback — generates detailed summaries from anomaly data
        without any LLM. Always works offline.
        """
        anomalies = data.get("anomalies", [])
        score = data.get("fraud_probability_score", 0)
        status = data.get("status", "UNKNOWN")
        filename = data.get("filename", "document")

        if not anomalies:
            return {
                "executive_summary": (
                    f"Forensic analysis of '{filename}' completed successfully. "
                    "No critical anomalies or tampering signals were detected. "
                    "The submitted document appears structurally consistent with "
                    "authentic bank-generated files. Standard verification is recommended."
                ),
                "hindi_summary": (
                    f"'{filename}' का फॉरेंसिक विश्लेषण सफलतापूर्वक पूरा हुआ। "
                    "कोई महत्वपूर्ण विसंगति या छेड़छाड़ के संकेत नहीं मिले। "
                    "प्रस्तुत दस्तावेज़ प्रामाणिक बैंक-जनित फ़ाइलों के अनुरूप प्रतीत होता है।"
                ),
                "reviewer_notes": "No anomalies detected. Standard verification recommended."
            }

        # Categorize anomalies
        critical = [a for a in anomalies if a.get("risk_level") == "Critical"]
        high = [a for a in anomalies if a.get("risk_level") == "High"]
        medium = [a for a in anomalies if a.get("risk_level") == "Medium"]
        low = [a for a in anomalies if a.get("risk_level") == "Low"]

        # Build executive summary
        summary_parts = [
            f"Forensic analysis of '{filename}' detected {len(anomalies)} anomalies "
            f"(Fraud Probability: {score}%, Status: {status})."
        ]

        if critical:
            summary_parts.append(
                f"\n\n[CRITICAL] ({len(critical)}): "
                + "; ".join(a.get("type", "Unknown") for a in critical) + "."
            )
        if high:
            summary_parts.append(
                f"\n[HIGH] ({len(high)}): "
                + "; ".join(a.get("type", "Unknown") for a in high) + "."
            )
        if medium:
            summary_parts.append(
                f"\n[MEDIUM] ({len(medium)}): "
                + "; ".join(a.get("type", "Unknown") for a in medium) + "."
            )
        if low:
            summary_parts.append(
                f"\n[LOW] ({len(low)}): "
                + "; ".join(a.get("type", "Unknown") for a in low) + "."
            )

        # Add top 3 most important anomaly descriptions
        top_anomalies = (critical + high + medium)[:3]
        if top_anomalies:
            summary_parts.append("\n\nKey Findings:")
            for i, a in enumerate(top_anomalies, 1):
                summary_parts.append(f"\n{i}. {a.get('description', 'No description available.')}")

        exec_summary = " ".join(summary_parts)

        # Hindi summary
        hindi_parts = [
            f"'{filename}' के फॉरेंसिक विश्लेषण में {len(anomalies)} विसंगतियाँ मिलीं "
            f"(धोखाधड़ी संभावना: {score}%, स्थिति: {status})।"
        ]
        if critical:
            hindi_parts.append(f" {len(critical)} गंभीर (Critical) संकेत पाए गए।")
        if high:
            hindi_parts.append(f" {len(high)} उच्च (High) गंभीरता के संकेत पाए गए।")
        if medium:
            hindi_parts.append(f" {len(medium)} मध्यम (Medium) संकेत पाए गए।")

        # Reviewer notes
        notes_parts = []
        if critical or high:
            notes_parts.append(
                f"WARNING: {len(critical) + len(high)} high-priority findings require immediate manual review."
            )
        for a in top_anomalies:
            notes_parts.append(f"• Verify: {a.get('type', 'Unknown')} — {a.get('description', '')[:100]}")

        if score >= 50:
            notes_parts.append("RECOMMENDATION: HIGH RISK — Escalate for senior review before processing.")
        elif score >= 20:
            notes_parts.append("RECOMMENDATION: SUSPICIOUS — Additional verification needed.")
        else:
            notes_parts.append("RECOMMENDATION: Low risk — standard processing can proceed.")

        return {
            "executive_summary": exec_summary,
            "hindi_summary": " ".join(hindi_parts),
            "reviewer_notes": "\n".join(notes_parts)
        }


summary_generator = SummaryGenerator()
