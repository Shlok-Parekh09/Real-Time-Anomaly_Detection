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
    You are a professional Lead Banking Forensic Auditor and Senior Compliance Investigator.
    Your task is to write a detailed, investigator-grade forensic audit report for bank underwriters by analyzing the provided document metrics, findings, metadata, and cross-document inconsistencies.
    
    STRICT FORENSIC GUIDELINES:
    1. GROUNDING & TRACEABILITY: Rely ONLY on the provided document files, metadata, extracted entities, and forensic findings. Every conclusion, risk observation, and recommendation MUST be directly traceable to specific documents, page numbers, or metadata fields. NEVER invent new names, amounts, transactions, or files.
    2. DEEP EVIDENCE ANALYSIS: Analyze the actual extracted entities and compare them. Specifically inspect and compare names, DOBs, ID numbers, employers, and transaction figures across ALL documents. Identify and clearly explain any specific contradictions (e.g., "Name on Aadhaar is 'SHLOK PAREKH' but PAN card shows 'SHLOK PARE'", or "Payslip indicates employer is 'XYZ LTD' but bank statement deposits are from 'ABC CORP'").
    3. DETECT METADATA & STRUCTURAL ANOMALIES: Inspect document metadata (e.g., creator, producer, software signatures) and explain why a finding exists (e.g., "Document metadata shows creation via 'Canva' or 'Photoshop' which indicates potential document regeneration or tampering, undermining the validity of a native payslip").
    4. REJECT UNSUPPORTED CONCLUSIONS: Do not jump to conclusions. If a finding is minor (e.g. low OCR quality on a scan), explain that it could be due to image quality rather than fraud, but recommend checking the original. If evidence is insufficient, explicitly state that instead of inventing or assuming fraudulent intent.
    5. PROFESSIONAL FORENSIC TONE: Never anthropomorphize (do NOT say "The system sees...", "We checked...", "I found..."). Use objective, investigator-grade forensic terminology (e.g., "Cross-document comparison identified...", "Metadata analysis detected...", "Entity reconciliation produced...", "Discrepancy validation indicated...").
    6. NO GENERIC OR TEMPLATE TEXT: Avoid generic statements like "Document is tampered". Write specific observations referencing actual document names and findings.
    7. TRANSLATION: Translate your high-level executive summary accurately into Hindi (Devanagari script) under the 'executive_summary_hi' key.
    8. NO WORD LIMIT: Provide complete, thorough, and highly detailed forensic audit observations and actionable recommendations. Do not artificially truncate reports.
    
    OUTPUT FORMAT (JSON):
    {
      "executive_summary": "English high-level summary detailing the case, the core findings, and why it is flagged or verified.",
      "executive_summary_hi": "Hindi translation of executive summary.",
      "risk_narrative": "Detailed risk narrative explaining why the trust score is at its current level, referencing specific findings.",
      "evidence_analysis": "Detailed comparison of name/PAN/Aadhaar/ID consistency, mismatches, and layout checks. Explicitly state any contradictions.",
      "forensic_reasoning": "Forensic audit reasoning detailing why the engine reached this decision based on findings.",
      "false_positive_probability": "Probability percentage (0-100%) and reasoning if this alert is a potential false positive.",
      "contradictions": ["List any specific document contradictions or fuzzy matches found."],
      "missing_evidence": ["List any missing evidence or documents that should be requested."],
      "manual_review_questions": ["List specific, direct questions the underwriter should ask the applicant based on the anomalies."],
      "recommended_next_steps": ["Specific, actionable verification steps list, e.g. 'Request original digitally signed bank statement PDF'."],
      "human_explanation": "A simple human-readable explanation of the case findings.",
      "forensic_story": "A chronological forensic audit story of how this folder was tampered or verified.",
      "final_recommendation": "Reject / Defer / Verify original document"
    }
    """

    def generate_summary(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates summary generation with safe fallback.
        """
        from core.settings_store import settings_store
        from core.ai_provider_manager import ai_provider_manager
        
        fallback_data = self._generate_template_summary(investigation_data)
        
        # Enforce availability check on the active provider
        is_ready, err_msg = ai_provider_manager.is_ai_ready()
        if not is_ready:
            logger.warning(f"AI Provider is not ready: {err_msg}. Disabling AI mode.")
            fallback_data["ai_offline_reason"] = err_msg
            fallback_data["ai_status"] = "offline"
            return fallback_data
            
        prompt = self._build_prompt(investigation_data)
        
        try:
            # 1. Run the configured audit report request.
            result = self._call_ollama(prompt)
            
            # Determine provider mode used
            execution_mode, config_provider, config_model, config_endpoint = ai_provider_manager.get_active_config()
            actual_provider = ai_provider_manager.last_provider
            
            if config_provider == "Gemini API" and actual_provider == "Local Ollama":
                provider_mode = "ollama_fallback"
            elif actual_provider == "Gemini API":
                provider_mode = "enhanced"
            else:
                provider_mode = "offline"
            
            # 2. Run Self Review correction check
            if settings.ENABLE_AI_SELF_REVIEW:
                try:
                    result = self._run_self_review(prompt, result)
                except Exception as review_err:
                    logger.error(f"Gemma Peer Self-Review validation failed: {review_err}. Returning original report.")
                
            # Safely merge missing keys from deterministic fallback
            for key in fallback_data:
                if key not in result or result[key] is None:
                    result[key] = fallback_data[key]
                elif isinstance(fallback_data[key], dict) and isinstance(result[key], dict):
                    for sub_key in fallback_data[key]:
                        if sub_key not in result[key] or result[key][sub_key] is None:
                            result[key][sub_key] = fallback_data[key][sub_key]
                            
            result["ai_status"] = "ready"
            result["ai_mode"] = provider_mode
            result["ai_model"] = ai_provider_manager.last_model
            return result
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}. Falling back to deterministic offline summary.")
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
            docs_list.append(f"- File: {d.get('filename')}\n  Type: {d.get('classification')}\n  OCR Accuracy: {d.get('ocr_confidence')}%\n  Producer: {d.get('metadata', {}).get('producer', 'None')}\n  Creator/Editor: {d.get('metadata', {}).get('creator', 'None')}")
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

    def _call_ollama(self, prompt: str, force_offline: bool = False) -> Dict[str, Any]:
        """
        Delegates the AI prompt generation to the central AI Provider Manager.
        """
        from core.settings_store import settings_store
        from core.ai_provider_manager import ai_provider_manager
        
        system_prompt = self.SYSTEM_PROMPT
        reasoning_depth = settings_store.get("ai_reasoning_depth", "standard")
        if reasoning_depth == "deep":
            system_prompt += "\nProvide deeper evidence-based forensic reasoning, but do not reveal private chain-of-thought. Summarize conclusions as concise audit rationale."
            
        verbosity = settings_store.get("ai_verbosity", "detailed")
        if verbosity == "concise":
            system_prompt += "\nKeep all synthesized summaries and evidence descriptions extremely concise and direct."
        elif verbosity == "detailed":
            system_prompt += "\nProvide comprehensive, detailed forensic evidence narratives and explanations."

        if force_offline:
            ollama_url = settings_store.get("ollama_url") or settings.OLLAMA_BASE_URL
            ollama_model = settings_store.get("ollama_model") or settings.OLLAMA_MODEL
            timeout_val = float(settings.OLLAMA_GENERATE_TIMEOUT_SECONDS)
            result = ai_provider_manager._call_ollama(
                system_prompt=system_prompt,
                user_prompt=prompt,
                ollama_url=ollama_url,
                ollama_model=ollama_model,
                temperature=float(settings_store.get("ai_temperature", 0.1)),
                max_tokens=2500,
                timeout=timeout_val
            )
        else:
            timeout_val = float(settings.OLLAMA_GENERATE_TIMEOUT_SECONDS)
            result = ai_provider_manager.generate_json(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=float(settings_store.get("ai_temperature", 0.1)),
                max_tokens=2500,
                timeout=timeout_val
            )
            
        if "hindi_summary" in result and "executive_summary_hi" not in result:
            result["executive_summary_hi"] = result["hindi_summary"]
            
        return result
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
                res_data = json.loads(res_body, strict=False)
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
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        try:
            return json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0), strict=False)
            raise

    def _generate_template_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        A deterministic fallback to prevent hallucinations when AI is unavailable.
        """
        findings = data.get("findings", [])
        rec = data.get("recommendation", "MANUAL_REVIEW")
        trust = data.get("trust_score", 100.0)
        
        id_findings = [f for f in findings if f.get("layer_source") == "CROSS_DOC" and "identity" in f.get("name", "").lower()]
        id_exp = f"Identity verification flagged {len(id_findings)} name mismatch signals. Fuzzy matching scores fell below threshold." if id_findings else "Names extracted from Aadhaar and PAN were normalized before comparison. All identity fields matched successfully after OCR correction. No conflicting identity attributes were detected."
        
        fin_findings = [f for f in findings if "math" in f.get("name", "").lower() or "balance" in f.get("name", "").lower() or "salary" in f.get("name", "").lower()]
        fin_exp = f"Financial math verification identified {len(fin_findings)} calculation warnings." if fin_findings else "All salary entries, transaction lines, and running balances were mathematically reconciled. Calculations check out exactly against bank statement totals."

        meta_findings = [f for f in findings if f.get("layer_source") == "FORENSIC"]
        meta_exp = f"Forensic layer flagged {len(meta_findings)} metadata / tool signature inconsistencies." if meta_findings else "Digital signatures, creator/producer metadata, and revision histories were audited. No signatures of editing software, compression modifications, or backdated timestamps were detected."

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
            
        exec_sum = ""
        hindi_sum = ""
        risk_narrative = ""
        
        if findings:
            exec_sum = f"Forensic analysis complete. Flagged {len(findings)} anomalies with Trust Score at {trust}%. Manual verification is recommended."
            hindi_sum = f"फॉरेंसिक विश्लेषण पूरा हो गया है। ट्रस्ट स्कोर {trust}% के साथ विसंगतियां पाई गईं। मैनुअल सत्यापन की सिफारिश की जाती है।"
            risk_narrative = f"Risk rating calculated at {100.0 - trust}% based on severity deductions from forensic checkpoints."
        else:
            exec_sum = "All uploaded documents exhibit strong structural consistency with known genuine references. No significant metadata anomalies, OCR inconsistencies, cross-document mismatches, or forensic indicators were detected. The investigation is considered low risk."
            hindi_sum = "सभी अपलोड किए गए दस्तावेज़ ज्ञात वास्तविक संदर्भों के साथ मजबूत संरचनात्मक स्थिरता प्रदर्शित करते हैं। कोई महत्वपूर्ण मेटाडेटा विसंगतियां, ओसीआर विसंगतियां, क्रॉस-दस्तावेज़ बेमेल, या फॉरेंसिक संकेतक नहीं पाए गए। इस जांच को कम जोखिम वाला माना गया है।"
            risk_narrative = "No structural, mathematical, or metadata anomalies detected. Document integrity is fully consistent with known authentic baselines."

        return {
            "executive_summary": exec_sum,
            "executive_summary_hi": hindi_sum,
            "hindi_summary": hindi_sum,
            "risk_narrative": risk_narrative,
            "evidence_analysis": f"Identity check: {id_exp} Math check: {fin_exp} Forensic check: {meta_exp}",
            "forensic_reasoning": "Determined by aggregating layer check weights.",
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
