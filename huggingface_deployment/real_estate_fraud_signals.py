"""
Real Estate Fraud Detection - 34 Specific Fraud Signals
Categorized by severity: High, Medium, Low
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any


# High Severity Fraud Signals (Critical - 12 signals)
HIGH_SEVERITY_SIGNALS = {
    "altered_bank_math": {
        "name": "Altered Bank Statement Math",
        "description": "The account balance numbers don't add up correctly based on the deposits and withdrawals shown.",
        "severity": "high",
        "weight": 40,
    },
    "pdf_metadata_anomalies": {
        "name": "PDF Metadata Anomalies",
        "description": "The document was edited using image software like Photoshop instead of being a direct download from the bank.",
        "severity": "high",
        "weight": 40,
    },
    "phantom_rental_income": {
        "name": "Phantom Rental Income",
        "description": "The claimed rental income does not appear in the actual bank account deposits.",
        "severity": "high",
        "weight": 38,
    },
    "forged_tax_transcripts": {
        "name": "Forged Tax Transcripts",
        "description": "The provided tax returns do not match the official IRS records.",
        "severity": "high",
        "weight": 40,
    },
    "reverse_occupancy": {
        "name": "Reverse Occupancy",
        "description": "An investment property is falsely claimed as a primary home to get a better loan rate.",
        "severity": "high",
        "weight": 35,
    },
    "undisclosed_mortgages": {
        "name": "Undisclosed Mortgages",
        "description": "Hidden loans or recent credit checks were left off the financial statement.",
        "severity": "high",
        "weight": 38,
    },
    "fabricated_leases": {
        "name": "Fabricated Leases",
        "description": "Lease agreements look fake, featuring non-existent tenants or impossible signature dates.",
        "severity": "high",
        "weight": 40,
    },
    "shell_company_concealment": {
        "name": "Shell Company Concealment",
        "description": "Fake companies are used to hide massive debts or past bankruptcies.",
        "severity": "high",
        "weight": 38,
    },
    "collusive_appraisals": {
        "name": "Collusive Appraisals",
        "description": "The buyer, seller, and appraiser are working together to fake a high property value.",
        "severity": "high",
        "weight": 40,
    },
    "straw_buyers": {
        "name": "Straw Buyers",
        "description": "A fake buyer is used to hide the true, unqualified investor.",
        "severity": "high",
        "weight": 40,
    },
    "bogus_earnest_money": {
        "name": "Bogus Earnest Money",
        "description": "The deposit money actually came from the seller to fake the buyer's financial strength.",
        "severity": "high",
        "weight": 40,
    },
    "identity_tampering": {
        "name": "Identity Document Tampering",
        "description": "Fake IDs or stolen social security numbers were detected.",
        "severity": "high",
        "weight": 40,
    },
}

# Medium Severity Fraud Signals (Strong Misrepresentation - 11 signals)
MEDIUM_SEVERITY_SIGNALS = {
    "sudden_account_seasoning": {
        "name": "Sudden Account Seasoning",
        "description": "Large, unexplained deposits were made right before the application to fake having more cash.",
        "severity": "medium",
        "weight": 25,
    },
    "inflated_market_rent": {
        "name": "Inflated Market Rent",
        "description": "The claimed rent is much higher than what normal apartments in the area charge.",
        "severity": "medium",
        "weight": 28,
    },
    "non_arms_length_leases": {
        "name": "Non-Arm's Length Leases",
        "description": "The tenants seem to be family members or business partners of the landlord.",
        "severity": "medium",
        "weight": 25,
    },
    "orphaned_property_expenses": {
        "name": "Orphaned Property Expenses",
        "description": "The bank statements show payments for properties that the borrower didn't claim to own.",
        "severity": "medium",
        "weight": 25,
    },
    "hidden_down_payment_loans": {
        "name": "Hidden Down Payment Loans",
        "description": "The down payment appears to be a hidden loan instead of a legitimate gift.",
        "severity": "medium",
        "weight": 28,
    },
    "unjustified_property_flipping": {
        "name": "Unjustified Property Flipping",
        "description": "The property was bought and quickly sold for much more without any clear improvements.",
        "severity": "medium",
        "weight": 25,
    },
    "unverifiable_liquidity": {
        "name": "Unverifiable Liquidity",
        "description": "Cash reserves are hidden in crypto or foreign accounts that can't be easily verified.",
        "severity": "medium",
        "weight": 22,
    },
    "commingled_funds": {
        "name": "Commingled Funds",
        "description": "Personal and business money are mixed together, making it hard to see true finances.",
        "severity": "medium",
        "weight": 20,
    },
    "geographic_inconsistencies": {
        "name": "Geographic Inconsistencies",
        "description": "The claimed primary home is located far away from where the person actually works.",
        "severity": "medium",
        "weight": 25,
    },
    "pfs_tax_discrepancies": {
        "name": "PFS vs. Tax Discrepancies",
        "description": "The claimed income is much higher than what was reported to the IRS.",
        "severity": "medium",
        "weight": 28,
    },
    "frequent_address_hopping": {
        "name": "Frequent Address Hopping",
        "description": "The credit report shows moving very often, which can be a sign of avoiding debt collectors.",
        "severity": "medium",
        "weight": 20,
    },
}

# Low Severity Fraud Signals (Red Flags - 11 signals)
LOW_SEVERITY_SIGNALS = {
    "inconsistent_name_variations": {
        "name": "Inconsistent Name Variations",
        "description": "Minor name differences across documents, like missing middle initials or varied maiden names.",
        "severity": "low",
        "weight": 8,
    },
    "missing_statement_pages": {
        "name": "Missing Statement Pages",
        "description": "The bank statement is missing pages, which could be an accident or a way to hide withdrawals.",
        "severity": "low",
        "weight": 12,
    },
    "sloppy_pfs_formatting": {
        "name": "Sloppy PFS Formatting",
        "description": "The financial statement is poorly filled out, with missing dates or broken Excel formulas.",
        "severity": "low",
        "weight": 8,
    },
    "irregular_rent_deposits": {
        "name": "Irregular Rent Deposits",
        "description": "Rent is paid in cash or through apps like Venmo at random times instead of a regular schedule.",
        "severity": "low",
        "weight": 10,
    },
    "stale_documentation": {
        "name": "Stale Documentation",
        "description": "The provided pay stubs or bank statements are too old (over 60-90 days).",
        "severity": "low",
        "weight": 10,
    },
    "handwritten_lease_corrections": {
        "name": "Handwritten Lease Corrections",
        "description": "The lease has handwritten changes crossed out without proper initials from both parties.",
        "severity": "low",
        "weight": 12,
    },
    "unexplained_micro_debits": {
        "name": "Unexplained Micro-Debits",
        "description": "Small, regular monthly charges that might indicate an undisclosed hidden debt.",
        "severity": "low",
        "weight": 8,
    },
    "newly_minted_llcs": {
        "name": "Newly Minted LLCs",
        "description": "A company claiming to own many properties was just created less than 30 days ago.",
        "severity": "low",
        "weight": 12,
    },
    "po_box_business_addresses": {
        "name": "PO Box Business Addresses",
        "description": "The business uses a PO Box or UPS Store instead of a real office location.",
        "severity": "low",
        "weight": 10,
    },
    "misaligned_job_titles": {
        "name": "Misaligned Job Titles",
        "description": "The person's job title does not match the massive salary they claim to make.",
        "severity": "low",
        "weight": 12,
    },
    "verbal_omissions": {
        "name": "Verbal Omissions",
        "description": "The borrower 'forgot' to mention some late payments or minor debts during the interview.",
        "severity": "low",
        "weight": 8,
    },
}


def detect_real_estate_fraud_signals(
    document_bytes: bytes,
    extracted_text: str,
    metadata: dict[str, Any],
    file_type: str,
) -> list[dict[str, Any]]:
    """
    Detect real estate fraud signals from document analysis.
    Returns list of detected fraud signals with severity and confidence.
    """
    detected_signals = []
    
    # 1. Check PDF Metadata Anomalies (HIGH)
    if file_type == "pdf":
        metadata_signal = _check_pdf_metadata_anomalies(metadata)
        if metadata_signal:
            detected_signals.append(metadata_signal)
    
    # 2. Check Altered Bank Math (HIGH)
    math_signal = _check_altered_bank_math(extracted_text)
    if math_signal:
        detected_signals.append(math_signal)
    
    # 3. Check Phantom Rental Income (HIGH)
    rental_signal = _check_phantom_rental_income(extracted_text)
    if rental_signal:
        detected_signals.append(rental_signal)
    
    # 4. Check Inflated Market Rent (MEDIUM)
    rent_signal = _check_inflated_market_rent(extracted_text)
    if rent_signal:
        detected_signals.append(rent_signal)
    
    # 5. Check Sudden Account Seasoning (MEDIUM)
    seasoning_signal = _check_sudden_account_seasoning(extracted_text)
    if seasoning_signal:
        detected_signals.append(seasoning_signal)
    
    # 6. Check Missing Statement Pages (LOW)
    missing_pages_signal = _check_missing_statement_pages(extracted_text)
    if missing_pages_signal:
        detected_signals.append(missing_pages_signal)
    
    # 7. Check Stale Documentation (LOW)
    stale_signal = _check_stale_documentation(extracted_text)
    if stale_signal:
        detected_signals.append(stale_signal)
    
    # 8. Check Irregular Rent Deposits (LOW)
    irregular_signal = _check_irregular_rent_deposits(extracted_text)
    if irregular_signal:
        detected_signals.append(irregular_signal)
    
    return detected_signals


def _check_pdf_metadata_anomalies(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Check for PDF created with editing software (HIGH severity)."""
    signal_def = HIGH_SEVERITY_SIGNALS["pdf_metadata_anomalies"]
    
    # Check creator and producer fields
    creator = str(metadata.get("Creator", "")).lower()
    producer = str(metadata.get("Producer", "")).lower()
    
    editing_software = [
        "photoshop", "illustrator", "gimp", "canva", "figma",
        "sketch", "affinity", "inkscape", "corel", "paint.net",
        "pixlr", "photoscape", "fotor", "befunky", "snapseed"
    ]
    
    detected_software = []
    for software in editing_software:
        if software in creator or software in producer:
            detected_software.append(software)
    
    if detected_software:
        return {
            "id": "pdf-metadata-anomalies",
            "name": signal_def["name"],
            "severity": signal_def["severity"],
            "summary": f"Document created with editing software: {', '.join(detected_software)}",
            "description": signal_def["description"],
            "evidence": [f"Creator: {creator}", f"Producer: {producer}"],
            "confidence": 0.95,
            "weight": signal_def["weight"],
        }
    
    return None


def _check_altered_bank_math(text: str) -> dict[str, Any] | None:
    """Check if bank statement math doesn't add up (HIGH severity)."""
    signal_def = HIGH_SEVERITY_SIGNALS["altered_bank_math"]
    
    # Extract financial amounts
    from financial_validator import validate_bank_statement_math
    
    validation = validate_bank_statement_math(text)
    
    if validation.get("has_balance_mismatch"):
        return {
            "id": "altered-bank-math",
            "name": signal_def["name"],
            "severity": signal_def["severity"],
            "summary": "Running balances do not match calculated values",
            "description": signal_def["description"],
            "evidence": [str(validation)],
            "confidence": 0.98,
            "weight": signal_def["weight"],
        }
    
    return None


def _check_phantom_rental_income(text: str) -> dict[str, Any] | None:
    """Check for rental income claims without corresponding deposits (HIGH severity)."""
    signal_def = HIGH_SEVERITY_SIGNALS["phantom_rental_income"]
    
    text_lower = text.lower()
    
    # Look for rental income keywords
    rental_keywords = ["rental income", "rent roll", "monthly rent", "lease payment"]
    has_rental_claims = any(keyword in text_lower for keyword in rental_keywords)
    
    # Look for deposit keywords
    deposit_keywords = ["deposit", "credit", "paid in", "received"]
    has_deposits = any(keyword in text_lower for keyword in deposit_keywords)
    
    # If rental income claimed but no deposits found
    if has_rental_claims and not has_deposits:
        return {
            "id": "phantom-rental-income",
            "name": signal_def["name"],
            "severity": signal_def["severity"],
            "summary": "Rental income claimed but no corresponding deposits found",
            "description": signal_def["description"],
            "evidence": ["Rental income mentioned without deposit records"],
            "confidence": 0.85,
            "weight": signal_def["weight"],
        }
    
    return None


def _check_inflated_market_rent(text: str) -> dict[str, Any] | None:
    """Check for rental rates significantly above market (MEDIUM severity)."""
    signal_def = MEDIUM_SEVERITY_SIGNALS["inflated_market_rent"]
    
    # Extract rent amounts
    rent_pattern = r'rent[:\s]+[\$£€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    matches = re.findall(rent_pattern, text.lower())
    
    if matches:
        try:
            rents = [float(m.replace(',', '')) for m in matches]
            avg_rent = sum(rents) / len(rents)
            
            # If average rent is suspiciously high (>$5000/month for typical units)
            if avg_rent > 5000:
                return {
                    "id": "inflated-market-rent",
                    "name": signal_def["name"],
                    "severity": signal_def["severity"],
                    "summary": f"Average rent of ${avg_rent:.2f} appears inflated",
                    "description": signal_def["description"],
                    "evidence": [f"Rent amounts: {rents}"],
                    "confidence": 0.75,
                    "weight": signal_def["weight"],
                }
        except:
            pass
    
    return None


def _check_sudden_account_seasoning(text: str) -> dict[str, Any] | None:
    """Check for large deposits 30-60 days before application (MEDIUM severity)."""
    signal_def = MEDIUM_SEVERITY_SIGNALS["sudden_account_seasoning"]
    
    # Look for large deposit patterns
    large_deposit_pattern = r'deposit[:\s]+[\$£€]?\s*([5-9]\d{3,}|[1-9]\d{4,})'
    matches = re.findall(large_deposit_pattern, text.lower())
    
    if len(matches) >= 2:  # Multiple large deposits
        return {
            "id": "sudden-account-seasoning",
            "name": signal_def["name"],
            "severity": signal_def["severity"],
            "summary": f"Found {len(matches)} large deposits suggesting account seasoning",
            "description": signal_def["description"],
            "evidence": [f"Large deposits detected: {len(matches)}"],
            "confidence": 0.70,
            "weight": signal_def["weight"],
        }
    
    return None


def _check_missing_statement_pages(text: str) -> dict[str, Any] | None:
    """Check for missing pages in bank statement (LOW severity)."""
    signal_def = LOW_SEVERITY_SIGNALS["missing_statement_pages"]
    
    # Look for page numbering
    page_pattern = r'page\s+(\d+)\s+of\s+(\d+)'
    matches = re.findall(page_pattern, text.lower())
    
    if matches:
        for current, total in matches:
            if int(current) != int(total):
                return {
                    "id": "missing-statement-pages",
                    "name": signal_def["name"],
                    "severity": signal_def["severity"],
                    "summary": f"Statement shows page {current} of {total} but may be incomplete",
                    "description": signal_def["description"],
                    "evidence": [f"Page numbering: {current} of {total}"],
                    "confidence": 0.60,
                    "weight": signal_def["weight"],
                }
    
    return None


def _check_stale_documentation(text: str) -> dict[str, Any] | None:
    """Check for outdated documents (LOW severity)."""
    signal_def = LOW_SEVERITY_SIGNALS["stale_documentation"]
    
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    matches = re.findall(date_pattern, text)
    
    if matches:
        parsed_dates = []
        for date_str in matches:
            for date_format in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%y", "%m/%d/%y"):
                try:
                    parsed_dates.append(datetime.strptime(date_str, date_format))
                    break
                except ValueError:
                    continue

        if parsed_dates:
            oldest_relevant_date = min(parsed_dates)
            age_days = (datetime.now() - oldest_relevant_date).days
            if age_days > 90:
                return {
                    "id": "stale-documentation",
                    "name": signal_def["name"],
                    "severity": signal_def["severity"],
                    "summary": f"Document date is {age_days} days old",
                    "description": signal_def["description"],
                    "evidence": [f"Oldest parsed date: {oldest_relevant_date.date().isoformat()}", f"Age: {age_days} days"],
                    "confidence": 0.65,
                    "weight": signal_def["weight"],
                }
    
    return None


def _check_irregular_rent_deposits(text: str) -> dict[str, Any] | None:
    """Check for cash/P2P rent payments (LOW severity)."""
    signal_def = LOW_SEVERITY_SIGNALS["irregular_rent_deposits"]
    
    text_lower = text.lower()
    
    # Look for P2P payment keywords
    p2p_keywords = ["venmo", "zelle", "cash app", "paypal", "cash payment"]
    found_p2p = [kw for kw in p2p_keywords if kw in text_lower]
    
    if found_p2p:
        return {
            "id": "irregular-rent-deposits",
            "name": signal_def["name"],
            "severity": signal_def["severity"],
            "summary": f"Rent payments via {', '.join(found_p2p)} detected",
            "description": signal_def["description"],
            "evidence": [f"P2P payment methods: {found_p2p}"],
            "confidence": 0.70,
            "weight": signal_def["weight"],
        }
    
    return None
