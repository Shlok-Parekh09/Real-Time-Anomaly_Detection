import json
import logging
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummaryGenerator:
    """
    Generates structured forensic analyst audit reports of investigations using AI (Gemma4:E4B).
    Converts rule-engine outputs into rich, investigator-style explanations.
    """
    
    SYSTEM_PROMPT = """
    You are a professional Banking Forensic Auditor and Senior Compliance Investigator.
    Your task is to analyze document audit data compiled by our automated checks and write an expert-level analyst explanation for bank underwriters.
    
    STRICT RULES:
    1. Rely ONLY on the provided findings, metadata, cross-document inconsistencies, and dataset matches.
    2. NEVER invent new files, names, transaction details, or findings. Ground all statements in evidence.
    3. Explain the "WHY" behind flagged items rather than repeating raw rule codes (e.g. explain OCR corruption or potential payslip regeneration pattern).
    4. Provide clear, professional, actionable recommendations (e.g. "Request original salary slips", "Verify PAN with issuing authority", "Validate employer through HR", "Obtain digitally signed PDF").
    5. Translate your high-level executive summary accurately into Hindi (Devanagari script) under the 'executive_summary_hi' key.
    6. Keep every string concise: maximum 35 words per field. Lists must contain at most 3 items.
    
    OUTPUT FORMAT (JSON):
    {
      "executive_summary": "English high-level summary explaining why this was flagged.",
      "executive_summary_hi": "Hindi translation of executive summary.",
      "risk_narrative": "Comprehensive risk explanation of why the trust score is at its current level.",
      "evidence_analysis": "Detailed explanation of name/PAN/Aadhaar/ID consistency, mismatches, and layout checks.",
      "confidence_reasoning": "Reasoning detailing why the engine confidence is high/low/medium.",
      "false_positive_probability": "Probability percentage (0-100%) and reasoning if this alert is a potential false positive.",
      "contradictions": ["List any document contradictions or fuzzy matches found."],
      "missing_evidence": ["List any missing evidence or documents that should be requested."],
      "manual_review_questions": ["List specific review questions the underwriter should ask the applicant."],
      "recommended_next_steps": ["Actionable verification steps list, e.g. Obtain net banking PDF."],
      "human_explanation": "A simple human explanation of the case findings.",
      "forensic_story": "A chronological forensic audit story of how this folder was tampered or verified.",
      "final_recommendation": "Reject / Defer / Verify original document"
    }
    """

    def generate_summary(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates summary generation with safe fallback.
        Refuses AI mode if Gemma4:E4B is not ready.
        """
        from core.system_state import startup_time_log
        
        fallback_data = self._generate_template_summary(investigation_data)
        
        # Enforce strict Gemma4:E4B availability check
        if startup_time_log.get("ai") != "ready":
            logger.warning("Gemma4:E4B model is not loaded or ready. Disabling AI mode.")
            fallback_data["ai_offline_reason"] = startup_time_log.get("reason", "Gemma4:E4B not loaded")
            fallback_data["ai_status"] = "offline"
            return fallback_data
            
        prompt = self._build_prompt(investigation_data)
        
        try:
            # 1. Run main Gemma audit report request
            result = self._call_ollama(prompt)
            
            # 2. Run Self Review correction check
            if settings.ENABLE_AI_SELF_REVIEW:
                try:
                    result = self._run_self_review(prompt, result)
                except Exception as review_err:
                    logger.error(f"Gemma Peer Self-Review validation failed: {review_err}. Returning original report.")
                
            # Safely merge missing keys from template fallback
            for key in fallback_data:
                if key not in result or result[key] is None:
                    result[key] = fallback_data[key]
                elif isinstance(fallback_data[key], dict) and isinstance(result[key], dict):
                    for sub_key in fallback_data[key]:
                        if sub_key not in result[key] or result[key][sub_key] is None:
                            result[key][sub_key] = fallback_data[key][sub_key]
                            
            result["ai_status"] = "ready"
            result["ai_mode"] = "ollama"
            result["ai_model"] = settings.OLLAMA_MODEL
            return result
        except Exception as e:
            logger.error(f"Gemma summary generation failed: {e}. Falling back to template summary.")
            fallback_data["ai_offline_reason"] = str(e)
            fallback_data["ai_status"] = "offline"
            return fallback_data

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """
        Serializes investigation results into an analyst prompt.
        """
        # Format findings with evidence
        findings_list = []
        for f in data.get("findings", []):
            ev_list = []
            for ev in f.get("evidence", []):
                ev_list.append(f"  - Evidence in {ev.get('document')} on page {ev.get('page')}: {ev.get('description')} [Text: '{ev.get('text')}']")
            ev_str = "\n".join(ev_list) if ev_list else "  - No specific coordinate evidence."
            findings_list.append(f"- Finding Name: {f['name']}\n  Severity: {f['severity']}\n  Source: {f['layer_source']}\n  Description: {f['description']}\n  Evidence Items:\n{ev_str}")
        findings_str = "\n\n".join(findings_list)
        
        # Format documents
        docs_list = []
        for d in data.get("documents", []):
            docs_list.append(f"- File: {d.get('filename')}\n  Type: {d.get('classification')}\n  OCR Confidence: {d.get('ocr_confidence')}%\n  Producer: {d.get('metadata', {}).get('producer', 'None')}\n  Creator/Editor: {d.get('metadata', {}).get('creator', 'None')}")
        docs_str = "\n".join(docs_list)
        
        # Format dataset similarity
        sim = data.get("dataset_similarity", {})
        gen_matches = []
        for m in sim.get("top_similar_genuine", []):
            gen_matches.append(f"  * {m.get('filename')} ({m.get('similarity_score')}% match) - Label: {m.get('label')}. Diffs: {', '.join(m.get('differences', []))}")
        fraud_matches = []
        for m in sim.get("top_similar_fraud", []):
            fraud_matches.append(f"  * {m.get('filename')} ({m.get('similarity_score')}% match) - Label: {m.get('label')}. Diffs: {', '.join(m.get('differences', []))}")
            
        sim_str = f"""- Best Overall Match Similarity: {sim.get('similarity_score')}%
- Is closest match a known fraud case? {sim.get('is_closest_fraud')}
- Explanatory baseline summary: {sim.get('explanation')}
- Top genuine references:
{chr(10).join(gen_matches) if gen_matches else '  No genuine baseline matches.'}
- Top fraudulent references:
{chr(10).join(fraud_matches) if fraud_matches else '  No fraudulent baseline matches.'}
"""

        prompt = f"""
        INVESTIGATION FORENSIC METRICS:
        - Case Context: {data.get('context')}
        - Trust Score: {data.get('trust_score')}/100
        - Confidence Score: {data.get('confidence_score')}/100
        - Rule Engine Suggestion: {data.get('recommendation')}
        
        DOCUMENT FILES & EXTRACTED METADATA:
        {docs_str or 'No documents.'}
        
        DETAILED FORENSIC FINDINGS & EVIDENCE ATTACHED:
        {findings_str or 'No findings detected.'}
        
        DATASET SIMILARITY & CASE-BASED REASONING (CBR) MATCHES:
        {sim_str}
        
        EVIDENCE RELATIONSHIP GRAPH NODES/EDGES:
        {json.dumps(data.get('evidence_graph', {}))}
        
        TIMELINE SEQUENCE LOGS:
        {json.dumps(data.get('timeline', []))}
        
        Please interpret these findings and provide the senior banking investigator audit report in the strict JSON format.
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
            "think": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 700
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
            with urllib.request.urlopen(req, timeout=settings.OLLAMA_GENERATE_TIMEOUT_SECONDS) as response:
                res_body = response.read().decode('utf-8')
                res_data = json.loads(res_body)
                content_str = res_data.get("message", {}).get("content", "")
                
                result = self._parse_json_content(content_str)
                
                if "hindi_summary" in result and "executive_summary_hi" not in result:
                    result["executive_summary_hi"] = result["hindi_summary"]
                    
                return result
        except Exception as e:
            logger.error(f"Error calling local Ollama service: {e}")
            raise e

    def _run_self_review(self, original_prompt: str, original_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs a secondary peer review request through Gemma to check for hallucinations, 
        unsupported claims, or logic flaws. Returns merged corrections.
        """
        review_prompt = f"""
        Original Audit Context & Findings:
        {original_prompt}
        
        Generated Forensic Report to Review:
        {json.dumps(original_report)}
        
        CRITICAL REVIEW TASK:
        Review the generated report against the original audit context.
        1. Identify any hallucinations or claims NOT supported by the findings.
        2. Identify any missing evidence points.
        3. Identify any weak reasoning.
        
        Return a JSON corrections report of this exact structure:
        {{
          "unsupported_claims_corrections": [
            "List any corrections for claims made in the report that are not found in the original audit context."
          ],
          "hallucinations_flagged": [
            "List any invented entities or numbers that must be corrected."
          ],
          "peer_reviewer_critique": "A brief expert audit critique of the report quality."
        }}
        """
        
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": "You are a senior banking forensic reviewer peer-reviewing an audit report. Only output strict JSON."},
                {"role": "user", "content": review_prompt}
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 250
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
            with urllib.request.urlopen(req, timeout=settings.OLLAMA_REVIEW_TIMEOUT_SECONDS) as response:
                res_body = response.read().decode('utf-8')
                res_data = json.loads(res_body)
                content_str = res_data.get("message", {}).get("content", "")
                review_result = self._parse_json_content(content_str)
                
                # Merge peer review critiques into report
                corrections = review_result.get("unsupported_claims_corrections", []) + review_result.get("hallucinations_flagged", [])
                if corrections:
                    logger.warning(f"[PEER REVIEW] Gemma detected potential hallucinations/unsupported claims: {corrections}")
                    critique_note = f"\n\n[Peer Review Audit: {review_result.get('peer_reviewer_critique', 'Adjustments applied.')}]"
                    original_report["executive_summary"] += critique_note
                    original_report["peer_review_corrections"] = corrections
                    
                return original_report
        except Exception as e:
            logger.error(f"Error running peer review: {e}")
            return original_report

    def _parse_json_content(self, content: str) -> Dict[str, Any]:
        """
        Parses Ollama JSON responses, tolerating markdown fences or brief prose.
        """
        if not content or not content.strip():
            raise ValueError("Ollama returned empty assistant content")

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\\s*", "", cleaned)
            cleaned = re.sub(r"\\s*```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\\{.*\\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """
        Calls Gemini API (Disabled).
        """
        return self._generate_template_summary({})

    def _generate_template_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        A deterministic fallback to prevent hallucinations when AI is unavailable.
        """
        findings = data.get("findings", [])
        rec = data.get("recommendation", "MANUAL_REVIEW")
        trust = data.get("trust_score", 100.0)
        
        id_findings = [f for f in findings if f.get("layer_source") == "CROSS_DOC" and "identity" in f.get("name", "").lower()]
        id_exp = f"Identity verification flagged {len(id_findings)} name mismatch signals. Fuzzy matching scores fell below threshold." if id_findings else "No identity inconsistencies detected across uploaded documents."
        
        fin_findings = [f for f in findings if "math" in f.get("name", "").lower() or "balance" in f.get("name", "").lower() or "salary" in f.get("name", "").lower()]
        fin_exp = f"Financial math verification identified {len(fin_findings)} calculation warnings." if fin_findings else "All transaction and salary calculations are mathematically consistent."

        meta_findings = [f for f in findings if f.get("layer_source") == "FORENSIC"]
        meta_exp = f"Forensic layer flagged {len(meta_findings)} metadata / tool signature inconsistencies." if meta_findings else "No editing signatures or timestamp modifications detected in PDF structures."

        sim_data = data.get("dataset_similarity", {})
        sim_score = sim_data.get("similarity_score", 0.0)
        sim_exp = f"This case matches known baseline models at {sim_score}% similarity. {sim_data.get('explanation', '')}"
        
        checks = []
        if id_findings:
            checks.append("Verify ID numbers with government databases.")
        if fin_findings:
            checks.append("Verify payslip basic pay matches deposits in bank statements.")
        if meta_findings:
            checks.append("Inspect file creator/producer metadata for Photoshop or Canva tags.")
        if not checks:
            checks.append("Conduct standard verification checklist.")
            
        exec_sum = "Forensic analysis complete. "
        if findings:
            exec_sum += f"Flagged {len(findings)} anomalies with Trust Score at {trust}%. Manual verification is recommended."
        else:
            exec_sum += f"No critical anomalies detected. Trust Score is {trust}%. Auto-approval recommended."
            
        hindi_sum = "फॉरेंसिक विश्लेषण पूरा हो गया है। "
        if findings:
            hindi_sum += f"ट्रस्ट स्कोर {trust}% के साथ विसंगतियां पाई गईं। मैनुअल सत्यापन की सिफारिश की जाती है।"
        else:
            hindi_sum += f"कोई विसंगति नहीं मिली। ट्रस्ट स्कोर {trust}% है।"

        return {
            "executive_summary": exec_sum,
            "executive_summary_hi": hindi_sum,
            "hindi_summary": hindi_sum,
            "risk_narrative": f"Risk rating calculated at {100.0 - trust}% based on severity deductions.",
            "evidence_analysis": f"Identity check: {id_exp} Math check: {fin_exp} Forensic check: {meta_exp}",
            "confidence_reasoning": "Determined by aggregating layer check weights.",
            "false_positive_probability": "15%" if findings else "0%",
            "contradictions": [f.get("name") for f in findings if "mismatch" in f.get("name", "").lower()],
            "missing_evidence": ["Net Banking PDF"] if findings else [],
            "manual_review_questions": ["Confirm salary transaction reference ID."] if findings else [],
            "recommended_next_steps": checks,
            "human_explanation": exec_sum,
            "forensic_story": f"Audit of applicant folder context '{data.get('context')}'. " + id_exp,
            "final_recommendation": "Verify Original Documents" if findings else "Approve Case"
        }

summary_generator = SummaryGenerator()
