"""
Local LLM Integration using Hugging Face Transformers
No external API calls - runs completely offline
"""
import json
import os
import logging
from typing import Dict, List, Any, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

logger = logging.getLogger(__name__)


class LocalLLM:
    """Local Language Model for fraud analysis"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipe = None
        # Use TinyLlama for free tier deployments (1.1B params, much smaller)
        self.model_name = os.getenv("LLM_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        self.initialized = False
        self._init_model()
    
    def _init_model(self):
        """Initialize the model (lazy loading)"""
        try:
            logger.info(f"[LLM] Initializing local model: {self.model_name}")
            
            # Check if CUDA is available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"[LLM] Using device: {device}")
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            if device == "cpu":
                self.model = self.model.to(device)
            
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=2000,
                temperature=0.1,
                do_sample=True,
                top_p=0.9,
            )
            
            self.initialized = True
            logger.info("[LLM] Model initialized successfully")
            
        except Exception as e:
            logger.error(f"[LLM] Failed to initialize model: {e}")
            self.initialized = False
            # Fallback to rule-based system
            logger.warning("[LLM] Falling back to rule-based analysis")
    
    def analyze_document(
        self,
        forensic_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze document for fraud using local LLM
        
        Args:
            forensic_data: Results from forensic engine
            context: Document context (metadata, text, etc.)
        
        Returns:
            Fraud analysis with signals and recommendations
        """
        if not self.initialized:
            return self._fallback_analysis(forensic_data, context)
        
        try:
            prompt = self._build_prompt(forensic_data, context)
            
            logger.info("[LLM] Generating fraud analysis...")
            response = self.pipe(prompt)[0]['generated_text']
            
            # Extract JSON from response
            result = self._extract_json(response)
            
            if result:
                logger.info(f"[LLM] Analysis complete: {len(result.get('fraud_signals', []))} signals")
                return result
            else:
                logger.warning("[LLM] Failed to extract JSON, using fallback")
                return self._fallback_analysis(forensic_data, context)
                
        except Exception as e:
            logger.error(f"[LLM] Error during analysis: {e}")
            return self._fallback_analysis(forensic_data, context)
    
    def _build_prompt(self, forensic_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build the prompt for the LLM"""
        
        system_prompt = """You are a fraud detection AI specialized in analyzing financial documents.
Analyze the provided document forensic data and return a detailed fraud analysis in JSON format.

Return ONLY valid JSON with this EXACT structure:
{
  "risk_score": 75.0,
  "trust_score": 25.0,
  "fraud_signals": [
    {
      "id": "signal-1",
      "name": "Signal Name",
      "severity": "high",
      "summary": "Brief summary",
      "description": "Detailed explanation",
      "evidence": ["Evidence 1", "Evidence 2"],
      "confidence": 0.9,
      "highlight_values": ["$1000", "2024-01-15"]
    }
  ],
  "ai_explanation": {
    "summary": "Brief overview",
    "likely_alteration": "What was altered",
    "recommended_action": "accept or reject"
  }
}

RULES:
- risk_score + trust_score = 100
- Include 3-7 fraud signals based on the forensic anomalies
- severity must be: high, medium, or low
- confidence must be between 0 and 1
- recommended_action must be: accept, reject, or review
- Analyze ALL provided forensic anomalies
- Be thorough and accurate"""

        user_content = f"""Document Analysis Request:

FILE: {context.get('file_name', 'unknown')}
TYPE: {context.get('file_type', 'unknown')}

FORENSIC ANOMALIES DETECTED ({forensic_data.get('anomaly_count', 0)}):
{json.dumps(forensic_data.get('anomalies', []), indent=2)}

METADATA:
{json.dumps(context.get('metadata', {}), indent=2)}

TEXT SAMPLE (first 1000 chars):
{context.get('text_content', '')[:1000]}

FORENSIC SCORE: {forensic_data.get('forensic_score', 0)}/100

Analyze this document for fraud and return JSON:"""

        return f"{system_prompt}\n\n{user_content}"
    
    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response"""
        import re
        
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find raw JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _fallback_analysis(
        self,
        forensic_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rule-based fallback analysis when LLM is unavailable
        """
        logger.info("[LLM] Using rule-based fallback analysis")
        
        anomalies = forensic_data.get('anomalies', [])
        forensic_score = forensic_data.get('forensic_score', 100.0)
        
        # Convert anomalies to fraud signals
        fraud_signals = []
        for i, anomaly in enumerate(anomalies[:10]):  # Limit to 10 signals
            signal = {
                "id": f"signal-{i+1}",
                "name": anomaly.get('type', 'Unknown').replace('_', ' ').title(),
                "severity": anomaly.get('severity', 'medium'),
                "summary": anomaly.get('message', 'Anomaly detected'),
                "description": self._generate_description(anomaly),
                "evidence": self._extract_evidence(anomaly, context),
                "confidence": self._calculate_confidence(anomaly),
                "highlight_values": []
            }
            fraud_signals.append(signal)
        
        # Calculate risk scores
        risk_score = 100.0 - forensic_score
        trust_score = forensic_score
        
        # Determine recommendation
        if risk_score >= 70:
            recommended_action = "reject"
            summary = "High risk document with multiple severe anomalies detected."
        elif risk_score >= 40:
            recommended_action = "review"
            summary = "Medium risk document requiring manual review."
        else:
            recommended_action = "accept"
            summary = "Low risk document with minimal anomalies."
        
        # Determine likely alteration
        likely_alteration = self._determine_alteration_type(anomalies)
        
        return {
            "risk_score": round(risk_score, 1),
            "trust_score": round(trust_score, 1),
            "fraud_signals": fraud_signals,
            "ai_explanation": {
                "summary": summary,
                "likely_alteration": likely_alteration,
                "recommended_action": recommended_action
            }
        }
    
    def _generate_description(self, anomaly: Dict[str, Any]) -> str:
        """Generate detailed description for anomaly"""
        anomaly_type = anomaly.get('type', 'unknown')
        message = anomaly.get('message', '')
        
        descriptions = {
            'metadata_missing': 'The document lacks standard metadata that should be present in legitimate documents.',
            'suspicious_creator': 'The document was created using image editing software, which is unusual for financial documents.',
            'date_inconsistency': 'The document contains inconsistent or impossible dates.',
            'invalid_date': 'One or more dates in the document are invalid or impossible.',
            'future_date': 'The document contains dates in the future.',
            'low_resolution': 'The image quality is suspiciously low for a scanned document.',
            'high_compression': 'The image has been highly compressed, which may hide alterations.',
            'suspicious_amounts': 'Financial amounts show suspicious patterns such as too many round numbers.',
            'formatting_inconsistency': 'Text formatting is inconsistent throughout the document.',
        }
        
        return descriptions.get(anomaly_type, message)
    
    def _extract_evidence(self, anomaly: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Extract evidence for anomaly"""
        evidence = []
        
        anomaly_type = anomaly.get('type', '')
        message = anomaly.get('message', '')
        
        # Add specific evidence based on type
        if 'metadata' in anomaly_type:
            metadata = context.get('metadata', {})
            if metadata:
                evidence.append(f"Creator: {metadata.get('creator', 'Missing')}")
                evidence.append(f"Producer: {metadata.get('producer', 'Missing')}")
        
        if 'date' in anomaly_type:
            evidence.append(f"Issue found: {message}")
        
        if 'resolution' in anomaly_type or 'compression' in anomaly_type:
            metadata = context.get('metadata', {})
            if 'width' in metadata:
                evidence.append(f"Resolution: {metadata.get('width')}x{metadata.get('height')}")
        
        # Add the original message as evidence
        if message and message not in evidence:
            evidence.append(message)
        
        return evidence if evidence else ["Anomaly detected in forensic analysis"]
    
    def _calculate_confidence(self, anomaly: Dict[str, Any]) -> float:
        """Calculate confidence score for anomaly"""
        severity = anomaly.get('severity', 'medium')
        
        severity_map = {
            'high': 0.9,
            'medium': 0.7,
            'low': 0.5
        }
        
        return severity_map.get(severity, 0.7)
    
    def _determine_alteration_type(self, anomalies: List[Dict[str, Any]]) -> str:
        """Determine the likely type of alteration based on anomalies"""
        types = [a.get('type', '') for a in anomalies]
        
        if any('metadata' in t for t in types):
            return "Metadata manipulation or document recreation"
        
        if any('date' in t for t in types):
            return "Date tampering or backdating"
        
        if any('financial' in t or 'amount' in t for t in types):
            return "Financial data manipulation"
        
        if any('compression' in t or 'resolution' in t for t in types):
            return "Image editing or re-scanning"
        
        if any('formatting' in t or 'text' in t for t in types):
            return "Text content modification"
        
        return "Multiple potential alterations detected"


# Global singleton instance
_llm_instance = None

def get_llm() -> LocalLLM:
    """Get or create the global LLM instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LocalLLM()
    return _llm_instance
