"""
Intelligent Document Analysis Engine
Provides AI-like analysis without requiring external API calls.
Uses advanced heuristics, pattern matching, and rule-based reasoning.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any


class IntelligentAnalyzer:
    """
    Advanced document analysis engine that mimics AI reasoning
    using sophisticated heuristics and pattern matching.
    """
    
    def __init__(self):
        self.fraud_patterns = self._load_fraud_patterns()
        self.legitimate_patterns = self._load_legitimate_patterns()
    
    def _load_fraud_patterns(self) -> dict[str, list[str]]:
        """Load known fraud indicators and patterns."""
        return {
            "editing_software": [
                "photoshop", "illustrator", "gimp", "canva", "paint.net",
                "pixlr", "photoscape", "fotor", "befunky", "snapseed",
                "affinity", "sketch", "figma", "inkscape", "krita",
                "paint shop", "corel", "acorn", "pixelmator"
            ],
            "suspicious_metadata": [
                "modified after creation", "multiple revisions", "incremental updates",
                "hidden sheets", "external links", "unreferenced strings",
                "recent modification", "creator mismatch", "producer mismatch"
            ],
            "financial_red_flags": [
                "perfectly rounded", "identical deposits", "missing expenses",
                "weekend transactions", "vague descriptions", "balance mismatch",
                "round numbers", "no decimals", "same amount", "repeated value",
                "no variation", "suspiciously consistent", "too perfect"
            ],
            "document_inconsistencies": [
                "font mismatch", "alignment issues", "compression artifacts",
                "resolution differences", "color space inconsistencies",
                "inconsistent spacing", "mixed fonts", "irregular margins",
                "overlapping text", "misaligned elements"
            ],
            "template_indicators": [
                "lorem ipsum", "placeholder", "sample text", "example",
                "your name here", "company name", "address here",
                "xxx", "000", "template", "draft", "test"
            ],
            "fabrication_markers": [
                "copy paste", "duplicate", "repeated section",
                "identical paragraph", "same sentence", "recycled content"
            ],
        }
    
    def _load_legitimate_patterns(self) -> dict[str, list[str]]:
        """Load patterns that indicate legitimate documents."""
        return {
            "bank_indicators": [
                "official letterhead", "bank logo", "regulatory text",
                "account number format", "sort code", "swift code", "iban"
            ],
            "payslip_indicators": [
                "employer details", "tax code", "national insurance",
                "pension contributions", "pay period", "employee number"
            ],
            "consistency_markers": [
                "uniform formatting", "consistent fonts", "proper alignment",
                "professional layout", "standard terminology"
            ],
        }
    
    def analyze_document_intelligence(
        self,
        file_name: str,
        risk_score: float,
        trust_score: float,
        signals: list[dict[str, Any]],
        recovered_version: dict[str, Any],
        validation_status: str,
        extracted_text: str,
        metadata: dict[str, Any],
    ) -> dict[str, str]:
        """
        Perform intelligent analysis of the document using advanced heuristics.
        This mimics AI reasoning without requiring external API calls.
        """
        
        # Analyze signal patterns
        high_severity_count = sum(1 for s in signals if s.get("severity") == "high")
        medium_severity_count = sum(1 for s in signals if s.get("severity") == "medium")
        low_severity_count = sum(1 for s in signals if s.get("severity") == "low")
        
        # Analyze X-ray recovery
        xray_available = recovered_version.get("available", False)
        xray_confidence = recovered_version.get("confidence", 0.0)
        changes_count = len(recovered_version.get("changes", []))
        
        # Analyze document content
        text_analysis = self._analyze_text_patterns(extracted_text)
        metadata_analysis = self._analyze_metadata_patterns(metadata)
        
        # Determine overall assessment
        if risk_score >= 70:
            risk_level = "HIGH RISK"
            action = "REJECT"
        elif risk_score >= 40:
            risk_level = "MEDIUM RISK"
            action = "REVIEW REQUIRED"
        else:
            risk_level = "LOW RISK"
            action = "ACCEPTABLE"
        
        # Generate intelligent summary
        summary = self._generate_summary(
            risk_level, high_severity_count, medium_severity_count,
            xray_available, changes_count, text_analysis
        )
        
        # Generate detailed alteration analysis
        likely_alteration = self._generate_alteration_analysis(
            signals, recovered_version, text_analysis, metadata_analysis
        )
        
        # Generate actionable recommendations
        recommended_action = self._generate_recommendations(
            action, risk_score, high_severity_count, xray_available,
            text_analysis, metadata_analysis
        )
        
        # Generate honest limitations
        limitations = self._generate_limitations(
            extracted_text, xray_available, metadata
        )
        
        return {
            "summary": summary,
            "likely_alteration": likely_alteration,
            "recommended_action": recommended_action,
            "limitations": limitations,
            "generated_by": "intelligent_heuristic_engine",
        }
    
    def _analyze_text_patterns(self, text: str) -> dict[str, Any]:
        """Analyze text for fraud patterns and legitimate indicators."""
        if not text or len(text) < 50:
            return {"quality": "insufficient", "indicators": []}
        
        lower_text = text.lower()
        
        # Check for fraud patterns
        fraud_indicators = []
        for category, patterns in self.fraud_patterns.items():
            matches = [p for p in patterns if p in lower_text]
            if matches:
                fraud_indicators.append({
                    "category": category,
                    "matches": matches,
                    "severity": "high" if len(matches) >= 2 else "medium"
                })
        
        # Check for legitimate patterns
        legitimate_indicators = []
        for category, patterns in self.legitimate_patterns.items():
            matches = [p for p in patterns if p in lower_text]
            if matches:
                legitimate_indicators.append({
                    "category": category,
                    "matches": matches
                })
        
        # Analyze text quality
        word_count = len(text.split())
        unique_words = len(set(text.lower().split()))
        vocabulary_richness = unique_words / word_count if word_count > 0 else 0
        
        # Check for copy-paste indicators
        repeated_phrases = self._find_repeated_phrases(text)
        
        # Advanced financial analysis
        financial_analysis = self._analyze_financial_patterns(text)
        
        # Check for template/placeholder text
        template_score = self._detect_template_usage(text)
        
        return {
            "quality": "good" if word_count > 100 else "limited",
            "word_count": word_count,
            "vocabulary_richness": vocabulary_richness,
            "fraud_indicators": fraud_indicators,
            "legitimate_indicators": legitimate_indicators,
            "repeated_phrases": repeated_phrases,
            "financial_analysis": financial_analysis,
            "template_score": template_score,
        }
    
    def _analyze_financial_patterns(self, text: str) -> dict[str, Any]:
        """Analyze financial data patterns for fraud indicators."""
        # Extract all numbers that look like currency amounts
        currency_pattern = r'[\$£€]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
        amounts = re.findall(currency_pattern, text)
        
        if not amounts:
            return {"has_financial_data": False}
        
        # Parse amounts to floats
        parsed_amounts = []
        for amount in amounts:
            try:
                # Remove currency symbols and commas
                clean = re.sub(r'[£$€,\s]', '', amount)
                parsed_amounts.append(float(clean))
            except ValueError:
                continue
        
        if not parsed_amounts:
            return {"has_financial_data": False}
        
        # Check for suspicious patterns
        rounded_count = sum(1 for amt in parsed_amounts if amt == round(amt, 0))
        rounded_percentage = (rounded_count / len(parsed_amounts)) * 100 if parsed_amounts else 0
        
        # Check for identical amounts
        amount_counts = Counter(parsed_amounts)
        identical_amounts = [amt for amt, count in amount_counts.items() if count >= 3]
        
        # Check for unrealistic consistency
        if len(set(parsed_amounts)) < len(parsed_amounts) * 0.3:
            consistency_flag = "high_repetition"
        else:
            consistency_flag = "normal_variation"
        
        # Check for suspiciously round numbers
        very_round = sum(1 for amt in parsed_amounts if amt in [1000, 2000, 3000, 5000, 10000, 15000, 20000, 25000, 50000])
        
        return {
            "has_financial_data": True,
            "total_amounts": len(parsed_amounts),
            "rounded_percentage": rounded_percentage,
            "identical_amounts": identical_amounts,
            "consistency_flag": consistency_flag,
            "very_round_count": very_round,
            "is_suspicious": rounded_percentage > 70 or len(identical_amounts) > 0 or very_round >= 3,
        }
    
    def _detect_template_usage(self, text: str) -> float:
        """Detect if document appears to be from a template or contains placeholders."""
        lower_text = text.lower()
        
        template_markers = [
            "lorem ipsum", "placeholder", "sample", "example",
            "your name", "company name", "address here",
            "xxx", "000000", "template", "draft", "test document",
            "[insert", "[add", "[enter", "{{", "}}", 
            "fill in", "replace this", "edit here"
        ]
        
        matches = sum(1 for marker in template_markers if marker in lower_text)
        
        # Check for excessive placeholder patterns like XXX, 000, etc.
        placeholder_patterns = [
            r'\bXXX+\b',
            r'\b000+\b',
            r'\[\s*\]',
            r'\(\s*\)',
        ]
        
        for pattern in placeholder_patterns:
            matches += len(re.findall(pattern, text))
        
        # Return score from 0-100
        return min(100, matches * 15)
    
    def _analyze_metadata_patterns(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Analyze metadata for suspicious patterns."""
        issues = []
        
        # Check for editing software
        software_fields = ["Producer", "Creator", "Software"]
        for field in software_fields:
            value = str(metadata.get(field, "")).lower()
            for suspicious in self.fraud_patterns["editing_software"]:
                if suspicious in value:
                    issues.append({
                        "type": "editing_software",
                        "field": field,
                        "value": value,
                        "severity": "high"
                    })
        
        # Check for date inconsistencies
        created = metadata.get("created") or metadata.get("CreationDate")
        modified = metadata.get("modified") or metadata.get("ModDate")
        if created and modified:
            issues.append({
                "type": "date_check",
                "created": str(created),
                "modified": str(modified),
                "severity": "low"
            })
        
        # Check for hidden content
        if metadata.get("hidden_sheets"):
            issues.append({
                "type": "hidden_content",
                "count": len(metadata.get("hidden_sheets", [])),
                "severity": "medium"
            })
        
        return {
            "issues": issues,
            "suspicious_count": len([i for i in issues if i["severity"] in ["high", "medium"]])
        }
    
    def _find_repeated_phrases(self, text: str, min_length: int = 20) -> list[str]:
        """Find repeated phrases that might indicate copy-paste."""
        words = text.split()
        repeated = []
        
        for length in range(5, 15):  # Check phrases of 5-15 words
            phrases = [" ".join(words[i:i+length]) for i in range(len(words) - length + 1)]
            phrase_counts = Counter(phrases)
            for phrase, count in phrase_counts.items():
                if count >= 2 and len(phrase) >= min_length:
                    repeated.append(phrase[:100])  # Limit length
        
        return repeated[:5]  # Return top 5
    
    def _generate_summary(
        self,
        risk_level: str,
        high_count: int,
        medium_count: int,
        xray_available: bool,
        changes_count: int,
        text_analysis: dict[str, Any],
    ) -> str:
        """Generate intelligent executive summary."""
        
        # Get financial and template analysis
        financial = text_analysis.get("financial_analysis", {})
        template_score = text_analysis.get("template_score", 0)
        
        if risk_level == "HIGH RISK":
            if high_count >= 3:
                summary = f"Document exhibits {high_count} high-severity fraud indicators including "
            else:
                summary = f"Document shows {high_count} critical fraud signal(s) with "
            
            if xray_available and changes_count > 0:
                summary += f"X-ray evidence of {changes_count} undisclosed modification(s). "
            
            fraud_cats = [ind["category"].replace("_", " ") for ind in text_analysis.get("fraud_indicators", [])]
            if fraud_cats:
                summary += f"Detected patterns: {', '.join(fraud_cats[:3])}. "
            
            # Add financial fraud indicators
            if financial.get("is_suspicious"):
                if financial.get("rounded_percentage", 0) > 70:
                    summary += f"Financial data shows {financial['rounded_percentage']:.0f}% rounded amounts (highly suspicious). "
                if financial.get("identical_amounts"):
                    summary += f"Repeated identical amounts detected: {len(financial['identical_amounts'])} patterns. "
            
            # Add template detection
            if template_score > 50:
                summary += f"Template usage detected (score: {template_score:.0f}/100). "
            
            summary += "Strong evidence of document tampering or fabrication."
        
        elif risk_level == "MEDIUM RISK":
            summary = f"Document contains {medium_count} medium-severity concern(s) "
            
            if xray_available:
                summary += "with X-ray recovery showing internal inconsistencies. "
            else:
                summary += "requiring additional verification. "
            
            # Add financial concerns
            if financial.get("is_suspicious"):
                summary += "Financial patterns show irregularities. "
            
            # Add template concerns
            if template_score > 30:
                summary += f"Some template elements detected. "
            
            summary += "Potential authenticity issues detected that warrant careful review."
        
        else:  # LOW RISK
            summary = "Document passes initial forensic screening with "
            
            if high_count == 0 and medium_count == 0:
                summary += "no significant fraud indicators detected. "
            else:
                summary += f"only {medium_count + high_count} minor concern(s). "
            
            legit_count = len(text_analysis.get("legitimate_indicators", []))
            if legit_count >= 2:
                summary += f"Contains {legit_count} legitimate document markers. "
            
            # Check if financial data looks normal
            if financial.get("has_financial_data") and not financial.get("is_suspicious"):
                summary += "Financial data shows normal variation patterns. "
            
            summary += "Appears consistent with authentic documentation."
        
        return summary
    
    def _generate_alteration_analysis(
        self,
        signals: list[dict[str, Any]],
        recovered_version: dict[str, Any],
        text_analysis: dict[str, Any],
        metadata_analysis: dict[str, Any],
    ) -> str:
        """Generate detailed analysis of likely alterations."""
        
        alterations = []
        
        # Analyze metadata issues
        metadata_issues = metadata_analysis.get("issues", [])
        high_meta_issues = [i for i in metadata_issues if i["severity"] == "high"]
        
        if high_meta_issues:
            for issue in high_meta_issues[:2]:
                if issue["type"] == "editing_software":
                    alterations.append(
                        f"Document metadata reveals creation/modification using {issue['value']}, "
                        f"which is image editing software rather than standard document generation tools. "
                        f"Legitimate bank statements and payslips are generated directly from banking systems, "
                        f"not created in photo editing applications."
                    )
        
        # Analyze X-ray findings
        if recovered_version.get("available"):
            changes = recovered_version.get("changes", [])
            if changes:
                removed_count = len([c for c in changes if c.get("type") == "removed"])
                added_count = len([c for c in changes if c.get("type") == "added"])
                
                if removed_count > 0 or added_count > 0:
                    alterations.append(
                        f"X-ray analysis recovered a previous document version showing {removed_count} "
                        f"deleted and {added_count} added content section(s). This indicates the document "
                        f"was modified after initial creation. "
                    )
                    
                    # Analyze specific changes
                    for change in changes[:3]:
                        if "account" in change.get("field", "").lower():
                            alterations.append(
                                f"Critical finding: Account-related information was altered. "
                                f"Previous value: '{change.get('previous_value', '')[:80]}...' "
                                f"This suggests potential identity fraud or account number manipulation."
                            )
                        elif "amount" in change.get("field", "").lower() or "balance" in change.get("field", "").lower():
                            alterations.append(
                                f"Financial data modification detected: {change.get('field')} was changed. "
                                f"This is a critical red flag indicating possible income inflation or balance manipulation."
                            )
        
        # Analyze fraud patterns from text
        fraud_indicators = text_analysis.get("fraud_indicators", [])
        for indicator in fraud_indicators[:2]:
            if indicator["category"] == "financial_red_flags":
                alterations.append(
                    f"Financial pattern analysis reveals {', '.join(indicator['matches'][:3])}. "
                    f"These patterns are statistically inconsistent with genuine financial documents "
                    f"and commonly appear in fabricated or altered statements."
                )
        
        # Analyze signal patterns
        high_signals = [s for s in signals if s.get("severity") == "high"]
        for signal in high_signals[:3]:
            if signal.get("name") == "Software":
                alterations.append(
                    f"Signal '{signal.get('name')}': {signal.get('summary')} "
                    f"This is particularly concerning as it indicates the document passed through "
                    f"non-standard processing that could facilitate tampering."
                )
        
        # Check for repeated content
        repeated = text_analysis.get("repeated_phrases", [])
        if len(repeated) >= 2:
            alterations.append(
                f"Document contains {len(repeated)} instances of repeated text blocks, "
                f"suggesting possible copy-paste manipulation or template-based fabrication."
            )
        
        if not alterations:
            return (
                "No significant tampering indicators detected. Document structure and content "
                "appear consistent with authentic generation. Metadata shows standard processing "
                "without suspicious editing software signatures. X-ray analysis (if available) "
                "reveals no undisclosed modifications."
            )
        
        return " ".join(alterations)
    
    def _generate_recommendations(
        self,
        action: str,
        risk_score: float,
        high_count: int,
        xray_available: bool,
        text_analysis: dict[str, Any],
        metadata_analysis: dict[str, Any],
    ) -> str:
        """Generate actionable recommendations for underwriters."""
        
        recommendations = []
        
        if action == "REJECT":
            recommendations.append(
                f"**REJECT APPLICATION** - Risk score of {risk_score:.1f}/100 exceeds acceptable threshold. "
            )
            
            if high_count >= 2:
                recommendations.append(
                    f"Multiple critical fraud indicators ({high_count}) detected. "
                    "Do not proceed with this application under any circumstances. "
                )
            
            if xray_available:
                recommendations.append(
                    "X-ray evidence confirms document modification. "
                )
            
            recommendations.append(
                "**Required Actions:** "
                "1) Flag applicant profile for fraud investigation. "
                "2) Request original documents directly from issuing institution. "
                "3) Verify applicant identity through independent channels. "
                "4) Report to fraud prevention team if pattern matches known fraud schemes."
            )
        
        elif action == "REVIEW REQUIRED":
            recommendations.append(
                f"**MANUAL REVIEW REQUIRED** - Risk score of {risk_score:.1f}/100 indicates potential issues. "
            )
            
            recommendations.append(
                "**Verification Steps:** "
                "1) Contact the stated financial institution directly to verify account and transaction history. "
                "2) Request additional supporting documents (utility bills, employment verification). "
                "3) Conduct enhanced due diligence on applicant background. "
            )
            
            if metadata_analysis.get("suspicious_count", 0) > 0:
                recommendations.append(
                    "4) Investigate metadata inconsistencies - request explanation for editing software usage. "
                )
            
            recommendations.append(
                "5) Compare provided documents against known authentic samples from the same institution. "
                "Do not approve until all concerns are satisfactorily resolved."
            )
        
        else:  # ACCEPTABLE
            recommendations.append(
                f"**PROCEED WITH STANDARD VERIFICATION** - Risk score of {risk_score:.1f}/100 is within acceptable range. "
            )
            
            recommendations.append(
                "Document passes automated fraud screening. "
                "Proceed with standard verification procedures: "
                "1) Confirm document details match application information. "
                "2) Verify account numbers and amounts are consistent across all submitted documents. "
                "3) Conduct routine identity verification checks. "
            )
            
            legit_count = len(text_analysis.get("legitimate_indicators", []))
            if legit_count >= 2:
                recommendations.append(
                    f"Document contains {legit_count} positive authenticity markers. "
                )
            
            recommendations.append(
                "While automated analysis shows no major concerns, always maintain standard due diligence practices."
            )
        
        return "".join(recommendations)
    
    def _generate_limitations(
        self,
        extracted_text: str,
        xray_available: bool,
        metadata: dict[str, Any],
    ) -> str:
        """Generate honest assessment of analysis limitations."""
        
        limitations = []
        
        limitations.append(
            "This analysis is based on document-level forensic examination and cannot: "
        )
        
        limitations.append(
            "1) Verify the authenticity of the issuing institution's digital signature or security features. "
        )
        
        limitations.append(
            "2) Confirm whether the account holder details match the applicant's actual identity. "
        )
        
        limitations.append(
            "3) Validate that transactions or employment details are genuine (requires direct verification with institutions). "
        )
        
        if not xray_available:
            limitations.append(
                "4) Detect all possible modifications - X-ray recovery was not available for this document type. "
            )
        
        if not extracted_text or len(extracted_text) < 100:
            limitations.append(
                "5) Perform comprehensive content analysis - text extraction was limited for this document. "
            )
        
        limitations.append(
            "**Critical:** Forensic analysis is a screening tool, not a definitive authenticity determination. "
            "Always verify critical information directly with issuing institutions before making lending decisions. "
            "Sophisticated forgeries may pass automated screening and require expert human review."
        )
        
        return "".join(limitations)
    
    def enrich_signal_description(self, signal: dict[str, Any], file_name: str) -> str:
        """Generate intelligent description for a fraud signal."""
        
        signal_name = signal.get("name", "")
        severity = signal.get("severity", "")
        summary = signal.get("summary", "")
        evidence = signal.get("evidence", [])
        
        # Generate context-aware description
        if signal_name == "X-ray":
            return (
                f"X-ray forensic analysis has recovered a previous version of this document from internal file history. "
                f"This indicates the document was modified after initial creation, which is highly unusual for authentic "
                f"bank-generated statements. Legitimate financial documents are typically created once and remain unmodified. "
                f"The presence of recoverable previous versions suggests intentional alteration, possibly to inflate income, "
                f"change account details, or modify transaction history. Underwriters should request original documents "
                f"directly from the issuing institution and investigate why modifications were made."
            )
        
        elif signal_name == "Software" or "software" in summary.lower():
            return (
                f"Document metadata contains signatures from image editing or design software rather than standard "
                f"document generation tools. Authentic bank statements and payslips are generated directly from banking "
                f"systems using PDF libraries or document processors, not created in Photoshop, GIMP, or similar applications. "
                f"The presence of editing software signatures indicates the document may have been created from scratch "
                f"using a template, or that an authentic document was opened and modified in editing software. "
                f"This is a critical red flag requiring immediate verification with the stated issuing institution."
            )
        
        elif "rounded" in summary.lower() or "identical" in summary.lower():
            return (
                f"Financial analysis reveals perfectly rounded amounts or repeated identical values that are statistically "
                f"inconsistent with genuine payroll processing. Real salary payments include tax calculations, pension "
                f"contributions, and other deductions that produce irregular amounts with pence/cents. When fraudsters "
                f"fabricate documents, they often use round numbers (£3,000.00, $5,000.00) because they're easier to remember "
                f"and type. Additionally, genuine salaries vary month-to-month due to overtime, bonuses, or tax code changes. "
                f"Repeated identical deposits suggest the document was created using copy-paste or a template rather than "
                f"genuine transaction data."
            )
        
        elif "balance" in summary.lower() or "math" in summary.lower():
            return (
                f"Mathematical validation reveals that the stated balances do not match the sum of transactions. "
                f"In authentic bank statements, opening balance + credits - debits must equal closing balance. "
                f"When this calculation doesn't match, it indicates either: (1) transactions were added/removed after "
                f"the document was generated, (2) amounts were manually changed, or (3) the entire document was fabricated "
                f"using a template without proper calculation. This is one of the most reliable fraud indicators because "
                f"fraudsters often focus on making individual transactions look realistic but fail to ensure the overall "
                f"mathematics is consistent."
            )
        
        elif "weekend" in summary.lower() or "backdated" in summary.lower():
            return (
                f"Transaction dates fall on weekends or non-processing days when banks typically don't process transactions. "
                f"Most retail banking transactions are processed Monday-Friday during business hours. While some automated "
                f"transactions may post on weekends, having multiple weekend transactions is unusual and suggests the dates "
                f"were manually entered without knowledge of banking processing schedules. This pattern commonly appears in "
                f"fabricated documents where fraudsters assign dates without considering operational banking calendars. "
                f"Verify these specific transactions directly with the bank."
            )
        
        elif "expense" in summary.lower() or "missing" in summary.lower():
            return (
                f"Document shows income deposits but lacks standard living expenses that appear in genuine personal accounts. "
                f"Real bank statements show regular spending on utilities, groceries, rent/mortgage, phone bills, insurance, "
                f"and other necessities. When a statement shows only deposits with no expenses, it suggests: (1) the account "
                f"is not actually used for daily banking, (2) expense transactions were selectively deleted, or (3) the "
                f"document was fabricated showing only income to inflate apparent financial stability. Genuine applicants "
                f"have normal spending patterns. The absence of these patterns is a significant red flag."
            )
        
        elif "metadata" in summary.lower() or "date" in summary.lower():
            return (
                f"Document metadata shows inconsistencies in creation and modification timestamps. Authentic documents "
                f"generated by banking systems have creation and modification dates that match or are very close together. "
                f"When these dates differ significantly, it indicates the document was opened and modified after initial "
                f"creation. While this alone isn't conclusive proof of fraud (documents can be legitimately edited for "
                f"redaction purposes), it warrants investigation when combined with other suspicious indicators. "
                f"Request explanation for why the document was modified and verify authenticity with the issuing institution."
            )
        
        elif "hidden" in summary.lower():
            return (
                f"Document contains hidden sheets or content that is not visible in normal viewing but remains in the file structure. "
                f"In Excel workbooks, hidden sheets can contain original data that was concealed after modification. Fraudsters "
                f"sometimes hide sheets containing authentic data and display only modified sheets, or hide calculation sheets "
                f"that would reveal inconsistencies. While hidden content can have legitimate purposes (template sheets, "
                f"calculation helpers), its presence in financial documents submitted for lending requires investigation. "
                f"Request the unhidden version and explanation for why content was concealed."
            )
        
        elif "payslip" in summary.lower() or "net pay" in summary.lower():
            return (
                f"Payslip analysis reveals mathematical inconsistencies between gross pay, deductions, and net pay. "
                f"In authentic payslips, net pay = gross pay - (tax + national insurance + pension + other deductions). "
                f"When this calculation doesn't match, or when deduction percentages are outside normal ranges (typically 20-45% "
                f"of gross), it indicates manual manipulation of figures. Fraudsters often inflate gross or net pay without "
                f"properly adjusting all related fields, creating mathematical impossibilities. Verify employment and salary "
                f"details directly with the stated employer."
            )
        
        else:
            # Generic intelligent description
            return (
                f"Forensic analysis detected: {summary}. This signal indicates potential document authenticity issues "
                f"that require verification. {' Evidence includes: ' + ', '.join(evidence[:3]) + '.' if evidence else ''} "
                f"While this finding alone may not be conclusive, it contributes to the overall risk assessment. "
                f"Underwriters should investigate this specific aspect and request supporting documentation or direct "
                f"verification from the issuing institution. Consider this signal in context with other detected indicators "
                f"to determine appropriate action."
            )


# Global analyzer instance
_analyzer = IntelligentAnalyzer()


def get_intelligent_analysis(
    file_name: str,
    risk_score: float,
    trust_score: float,
    signals: list[dict[str, Any]],
    recovered_version: dict[str, Any],
    validation_status: str,
    extracted_text: str,
    metadata: dict[str, Any],
) -> dict[str, str]:
    """Get intelligent analysis without requiring API key."""
    return _analyzer.analyze_document_intelligence(
        file_name, risk_score, trust_score, signals,
        recovered_version, validation_status, extracted_text, metadata
    )


def get_intelligent_signal_description(signal: dict[str, Any], file_name: str) -> str:
    """Get intelligent description for a signal without requiring API key."""
    return _analyzer.enrich_signal_description(signal, file_name)
