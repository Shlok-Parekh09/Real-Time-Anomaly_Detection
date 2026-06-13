import re
from typing import Dict, Any, List

class DocumentClassifier:
    """
    Identifies the type of document based on keywords and patterns in the text.
    """
    
    PATTERNS = {
        "Bank Statement": [
            r"(?i)bank\s+statement",
            r"(?i)account\s+summary",
            r"(?i)transaction\s+history",
            r"(?i)balance\s+as\s+of",
            r"(?i)deposits\s+and\s+credits",
            r"(?i)withdrawals\s+and\s+debits"
        ],
        "Payslip": [
            r"(?i)payslip",
            r"(?i)salary\s+statement",
            r"(?i)earnings\s+and\s+deductions",
            r"(?i)pay\s+period",
            r"(?i)employee\s+id",
            r"(?i)net\s+pay"
        ],
        "PAN": [
            r"(?i)permanent\s+account\s+number",
            r"(?i)income\s+tax\s+department",
            r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b" # PAN pattern
        ],
        "Aadhaar": [
            r"(?i)aadhaar",
            r"(?i)unique\s+identification\s+authority",
            r"\b\d{4}\s\d{4}\s\d{4}\b" # Aadhaar pattern
        ],
        "Utility Bill": [
            r"(?i)electricity\s+bill",
            r"(?i)water\s+bill",
            r"(?i)consumer\s+number",
            r"(?i)billing\s+period",
            r"(?i)previous\s+reading"
        ],
        "Lease Agreement": [
            r"(?i)lease\s+agreement",
            r"(?i)rental\s+agreement",
            r"(?i)landlord",
            r"(?i)tenant",
            r"(?i)monthly\s+rent"
        ],
        "Insurance Document": [
            r"(?i)insurance\s+policy",
            r"(?i)premium\s+amount",
            r"(?i)policy\s+number",
            r"(?i)sum\s+insured",
            r"(?i)coverage\s+period"
        ]
    }

    def classify(self, text: str) -> str:
        """
        Classify document based on text content.
        """
        if not text:
            return "Unknown"
            
        scores = {}
        for doc_type, regex_list in self.PATTERNS.items():
            score = 0
            for regex in regex_list:
                if re.search(regex, text):
                    score += 1
            if score > 0:
                scores[doc_type] = score
                
        if not scores:
            return "Unknown"
            
        # Return the doc type with the highest score
        return max(scores, key=scores.get)

document_classifier = DocumentClassifier()
