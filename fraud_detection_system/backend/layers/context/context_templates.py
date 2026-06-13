from typing import Dict, List, Any

CONTEXT_RULES = {
    "loan_approval": [
        "check_salary_consistency",
        "check_bank_balance",
        "check_employer_validity"
    ],
    "mortgage_underwriting": [
        "check_property_ownership",
        "check_property_valuation",
        "check_long_term_income"
    ],
    "kyc": [
        "check_identity_consistency",
        "check_address_validity",
        "check_document_authenticity"
    ],
    "tenant_screening": [
        "check_rental_history",
        "check_income_to_rent_ratio"
    ],
    "insurance_claims": [
        "check_claim_consistency",
        "check_policy_coverage"
    ],
    "credit_assessment": [
        "check_debt_to_income",
        "check_credit_score_consistency"
    ],
    "internal_audit": [
        "check_compliance_markers",
        "check_process_adherence"
    ]
}

def get_rules_for_context(context: str) -> List[str]:
    """
    Returns the list of validation rules for a given investigation context.
    """
    return CONTEXT_RULES.get(context.lower().replace(" ", "_"), [])
