import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummaryGenerator:
    """
    Generates human-readable summaries of investigations using AI.
    Includes strict hallucination protection.
    """
    
    SYSTEM_PROMPT = """
    You are a professional Banking Forensic Auditor. 
    Your task is to summarize document investigation findings for underwriters.
    
    STRICT RULES:
    1. Only use the PROVIDED Findings, Evidence, and Scores.
    2. NEVER invent new findings or fraud explanations.
    3. NEVER mention entities or documents not in the input.
    4. If information is missing, explicitly say 'Data not available'.
    5. Be concise and objective.
    6. Do NOT decide if something is fraud; explain WHY it was flagged.
    
    OUTPUT FORMAT (JSON):
    {
      "executive_summary": "English high-level summary",
      "hindi_summary": "Hindi translation of executive summary",
      "reviewer_notes": "Specific actionable notes for the investigator"
    }
    """

    def generate_summary(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates summary generation.
        """
        prompt = self._build_prompt(investigation_data)
        
        if settings.USE_LOCAL_LLM:
            try:
                return self._call_ollama(prompt)
            except Exception as e:
                logger.error(f"Local Ollama summary generation failed: {e}. Falling back to template summary.")
                return self._generate_template_summary(investigation_data)
        elif settings.GEMINI_API_KEY:
            try:
                return self._call_gemini(prompt)
            except Exception as e:
                logger.error(f"Gemini AI call failed: {e}. Falling back to template summary.")
                return self._generate_template_summary(investigation_data)
        else:
            return self._generate_template_summary(investigation_data)

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """
        Serializes investigation results into a prompt.
        """
        findings_str = "\n".join([
            f"- {f['name']} ({f['severity']}): {f['description']}" 
            for f in data.get("findings", [])
        ])
        
        prompt = f"""
        INVESTIGATION CONTEXT: {data.get('context')}
        TRUST SCORE: {data.get('trust_score')}/100
        CONFIDENCE SCORE: {data.get('confidence_score')}/100
        RECOMMENDATION: {data.get('recommendation')}
        
        FINDINGS:
        {findings_str or 'No findings detected.'}
        
        Provide the analysis in the requested JSON format.
        """
        return prompt

    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """
        Calls local Ollama API.
        """
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1
            },
            "format": "json"
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            # Short timeout to ensure we fail fast if Ollama is not ready
            with urllib.request.urlopen(req, timeout=12) as response:
                res_body = response.read().decode('utf-8')
                res_data = json.loads(res_body)
                content_str = res_data.get("message", {}).get("content", "")
                
                # Parse content as JSON
                result = json.loads(content_str)
                
                # Map keys to ensure both hindi_summary and executive_summary_hi exist
                if "hindi_summary" in result and "executive_summary_hi" not in result:
                    result["executive_summary_hi"] = result["hindi_summary"]
                elif "executive_summary_hi" in result and "hindi_summary" not in result:
                    result["hindi_summary"] = result["executive_summary_hi"]
                elif "executive_summary_hi" not in result and "hindi_summary" not in result:
                    result["executive_summary_hi"] = "Hindi summary not provided by model."
                    result["hindi_summary"] = "Hindi summary not provided by model."
                    
                return result
        except Exception as e:
            logger.error(f"Error calling local Ollama service: {e}")
            raise e

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """
        Calls Gemini API (Placeholder/Legacy).
        """
        return self._generate_template_summary({})

    def _generate_template_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        A deterministic fallback to prevent hallucinations when AI is unavailable.
        """
        findings = data.get("findings", [])
        rec = data.get("recommendation", "MANUAL_REVIEW")
        
        if not findings:
            exec_sum = "No critical anomalies or tampering signals were detected during the forensic analysis. The submitted documents appear structurally consistent."
            hindi_sum = "फॉरेंसिक विश्लेषण के दौरान कोई महत्वपूर्ण विसंगति या छेड़छाड़ के संकेत नहीं मिले। प्रस्तुत दस्तावेज संरचनात्मक रूप से सुसंगत प्रतीत होते हैं।"
            notes = "Standard verification recommended."
        else:
            high_count = sum(1 for f in findings if f["severity"] == "HIGH")
            exec_sum = f"Analysis detected {len(findings)} findings, including {high_count} high-severity signals. "
            exec_sum += f"Recommendation is {rec.replace('_', ' ')} based on detected inconsistencies."
            
            hindi_sum = f"विश्लेषण में {len(findings)} निष्कर्ष मिले, जिनमें {high_count} गंभीर संकेत शामिल हैं। "
            hindi_sum += f"विसंगतियों के आधार पर {rec} की सिफारिश की जाती है।"
            
            notes = "Review the coordinate-bound evidence for specific mismatch locations."

        return {
            "executive_summary": exec_sum,
            "hindi_summary": hindi_sum,
            "executive_summary_hi": hindi_sum,
            "reviewer_notes": notes
        }

summary_generator = SummaryGenerator()
