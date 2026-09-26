import re
from typing import Dict, Any, List
from datetime import datetime

class DateValidator:
    """
    Validates dates found in documents.
    """
    def validate(self, text: str) -> List[Dict[str, Any]]:
        findings = []

        # We already added some basic logic in financial_validator, but let's centralize here as requested
        date_patterns = [
            r'\b(30|31)[/-](02|2)\b',      # Feb 30/31
            r'\b(31)[/-](04|06|09|11|4|6|9)\b', # 31st of Apr, Jun, Sep, Nov
            r'\b(30|31)\s+(Feb|February)\b',
            r'\b(31)\s+(Apr|April|Jun|June|Sep|September|Nov|November)\b'
        ]

        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                findings.append({
                    "name": "Impossible Date Detected",
                    "severity": "HIGH",
                    "description": "Document contains a logically impossible date (e.g., February 31st).",
                    "evidence": [f"Matched text: {match.group(0)}"]
                })

        # Future date detection
        # Extract general dates
        general_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b'
        ]

        now = datetime.now()
        for pattern in general_patterns:
            for match in re.finditer(pattern, text):
                try:
                    parts = list(match.groups())
                    # Very rough heuristic to parse YYYY vs DD/MM
                    if len(parts[0]) == 4:
                        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    else:
                        y, m, d = int(parts[2]), int(parts[1]), int(parts[0])
                        # Indian vs US date format could flip month/day, so assume it's valid if either works,
                        # but check if year is in future

                    if y > now.year + 1 or (y == now.year and m > now.month and d > now.day):
                        # simple future date check (just checking year for strictness)
                        if y > now.year:
                            findings.append({
                                "name": "Future Date Detected",
                                "severity": "MEDIUM",
                                "description": f"A date in the future ({y}) was found in the document.",
                                "evidence": [f"Matched: {match.group(0)}"]
                            })
                except ValueError:
                    pass

        # Deduplicate
        unique_findings = []
        seen = set()
        for f in findings:
            key = f["name"] + str(f["evidence"])
            if key not in seen:
                seen.add(key)
                unique_findings.append(f)

        return unique_findings

date_validator = DateValidator()
