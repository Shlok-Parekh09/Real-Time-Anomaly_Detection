from typing import Dict, Any, List
from .financial_validator import extract_financial_amounts

class BalanceValidator:
    """
    Running-balance verification for bank statements.
    """
    def validate(self, text: str) -> List[Dict[str, Any]]:
        # This is a wrapper around the existing math logic in financial_validator
        # which already handles closing/opening balances.
        # But we can format it strictly for the investigation manager integration.
        # We will use the existing validate_bank_statement_math logic.

        from .financial_validator import validate_bank_statement_math
        results = validate_bank_statement_math(text)

        findings = []
        if results.get("validation_results"):
            for vr in results["validation_results"]:
                findings.append({
                    "name": vr["type"].replace("_", " ").title(),
                    "severity": vr["severity"].upper(),
                    "description": vr["description"],
                    "evidence": [f"Calculated differences. Opening: {vr.get('opening_balance')} Closing: {vr.get('closing_balance')}"]
                })

        return findings

balance_validator = BalanceValidator()
