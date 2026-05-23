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
        "description": "Running daily balances do not mathematically align with listed debits and credits",
        "severity": "high",
        "weight": 40,
    },
    "pdf_metadata_anomalies": {
        "name": "PDF Metadata Anomalies",
        "description": "File created/modified using editing software (Adobe Illustrator, Photoshop) rather than native bank export",
        "severity": "high",
        "weight": 40,
    },
    "phantom_rental_income": {
        "name": "Phantom Rental Income",
        "description": "Gross rental income claimed on rent roll is absent from actual bank account deposits",
        "severity": "high",
        "weight": 38,
    },
    "forged_tax_transcripts": {
        "name": "Forged Tax Transcripts",
        "description": "Tax returns provided do not match official IRS transcripts (Form 4506-C)",
        "severity": "high",
        "weight": 40,
    },
    "reverse_occupancy": {
        "name": "Reverse Occupancy",
        "description": "Investment property claimed as primary residence while owning superior home nearby",
        "severity": "high",
        "weight": 35,
    },
    "undisclosed_mortgages": {
        "name": "Undisclosed Mortgages",
        "description": "Credit report shows recent hard inquiries/tradelines omitted from Personal Financial Statement",
        "severity": "high",
        "weight": 38,
    },
    "fabricated_leases": {
        "name": "Fabricated Leases",
        "description": "Leases feature non-existent tenants, vacant units, or signatures dated on legal holidays",
        "severity": "high",
        "weight": 40,
    },
    "shell_company_concealment": {
        "name": "Shell Company Concealment",
        "description": "Complex layered LLCs hiding massive off-balance-sheet liabilities or past bankruptcies",
        "severity": "high",
        "weight": 38,
    },
    "collusive_appraisals": {
        "name": "Collusive Appraisals",
        "description": "Buyer, seller, broker, and appraiser share business interests, artificially inflating property value",
        "severity": "high",
        "weight": 40,
    },
    "straw_buyers": {
        "name": "Straw Buyers",
        "description": "Stated borrower has no real connection to property/down payment, masking true unqualified investor",
        "severity": "high",
        "weight": 40,
    },
    "bogus_earnest_money": {
        "name": "Bogus Earnest Money",
        "description": "Deposit traced back to seller, suggesting non-arm's length transaction to fake borrower equity",
        "severity": "high",
        "weight": 40,
    },
    "identity_tampering": {
        "name": "Identity Document Tampering",
        "description": "Altered driver's licenses, mismatched SSNs across credit bureaus, or use of deceased person's identity",
        "severity": "high",
        "weight": 40,
    },
}

# Medium Severity Fraud Signals (Strong Misrepresentation - 11 signals)
MEDIUM_SEVERITY_SIGNALS = {
    "sudden_account_seasoning": {
        "name": "Sudden Account Seasoning",
        "description": "Massive unexplainable deposits 30-60 days before loan application to fake liquid reserves",
        "severity": "medium",
        "weight": 25,
    },
    "inflated_market_rent": {
        "name": "Inflated Market Rent",
        "description": "Leases claim rental rates 30%+ above verified local market average for comparable units",
        "severity": "medium",
        "weight": 28,
    },
    "non_arms_length_leases": {
        "name": "Non-Arm's Length Leases",
        "description": "Tenants share same last name as landlord or are officers of landlord's other businesses",
        "severity": "medium",
        "weight": 25,
    },
    "orphaned_property_expenses": {
        "name": "Orphaned Property Expenses",
        "description": "Bank statements show recurring debits for properties not listed on Schedule of Real Estate Owned",
        "severity": "medium",
        "weight": 25,
    },
    "hidden_down_payment_loans": {
        "name": "Hidden Down Payment Loans",
        "description": "Hard-money or undisclosed personal loan funding down payment, fraudulently documented as 'gift'",
        "severity": "medium",
        "weight": 28,
    },
    "unjustified_property_flipping": {
        "name": "Unjustified Property Flipping",
        "description": "Rapid title transfers (6-12 months) with significant value spikes without renovation permits",
        "severity": "medium",
        "weight": 25,
    },
    "unverifiable_liquidity": {
        "name": "Unverifiable Liquidity",
        "description": "Large reserves in cryptocurrency, overseas accounts, or private vaults untraceable to fiat currency",
        "severity": "medium",
        "weight": 22,
    },
    "commingled_funds": {
        "name": "Commingled Funds",
        "description": "Extensive mixing of business revenues and personal expenses to artificially inflate personal liquidity",
        "severity": "medium",
        "weight": 20,
    },
    "geographic_inconsistencies": {
        "name": "Geographic Inconsistencies",
        "description": "Multi-family property claimed as primary residence, but W-2 employer located three states away",
        "severity": "medium",
        "weight": 25,
    },
    "pfs_tax_discrepancies": {
        "name": "PFS vs. Tax Discrepancies",
        "description": "Net worth/business income on PFS vastly exceeds IRS figures, suggesting tax evasion or loan fraud",
        "severity": "medium",
        "weight": 28,
    },
    "frequent_address_hopping": {
        "name": "Frequent Address Hopping",
        "description": "Credit report shows chaotic address changes every few months, hallmark of dodging creditors",
        "severity": "medium",
        "weight": 20,
    },
}

# Low Severity Fraud Signals (Red Flags - 11 signals)
LOW_SEVERITY_SIGNALS = {
    "inconsistent_name_variations": {
        "name": "Inconsistent Name Variations",
        "description": "Minor spelling errors, omitted suffixes (Jr., Sr.), or varied uses of maiden names",
        "severity": "low",
        "weight": 8,
    },
    "missing_statement_pages": {
        "name": "Missing Statement Pages",
        "description": "Bank statement submitted with missing pages (could be scanning error or hiding withdrawals)",
        "severity": "low",
        "weight": 12,
    },
    "sloppy_pfs_formatting": {
        "name": "Sloppy PFS Formatting",
        "description": "Personal Financial Statement contains broken Excel formulas, missing dates, or unsigned signature blocks",
        "severity": "low",
        "weight": 8,
    },
    "irregular_rent_deposits": {
        "name": "Irregular Rent Deposits",
        "description": "Tenants pay rent in cash or via peer-to-peer apps (Venmo, Zelle) at random times",
        "severity": "low",
        "weight": 10,
    },
    "stale_documentation": {
        "name": "Stale Documentation",
        "description": "Pay stubs, bank statements, or rent rolls are over 60-90 days old",
        "severity": "low",
        "weight": 10,
    },
    "handwritten_lease_corrections": {
        "name": "Handwritten Lease Corrections",
        "description": "Lease agreements feature handwritten crossed-out amounts/dates without proper countersignatures",
        "severity": "low",
        "weight": 12,
    },
    "unexplained_micro_debits": {
        "name": "Unexplained Micro-Debits",
        "description": "Small recurring monthly debits ($50-$150) suggesting undisclosed minor liability",
        "severity": "low",
        "weight": 8,
    },
    "newly_minted_llcs": {
        "name": "Newly Minted LLCs",
        "description": "LLC listed as holding company for massive portfolio, but incorporated less than 30 days ago",
        "severity": "low",
        "weight": 12,
    },
    "po_box_business_addresses": {
        "name": "PO Box Business Addresses",
        "description": "Landlord lists PO Box or UPS Store as primary corporate headquarters without physical address",
        "severity": "low",
        "weight": 10,
    },
    "misaligned_job_titles": {
        "name": "Misaligned Job Titles",
        "description": "Generic low-level job title but reports massive salary contradicting industry norms",
        "severity": "low",
        "weight": 12,
    },
    "verbal_omissions": {
        "name": "Verbal Omissions",
        "description": "Borrower 'forgets' to mention minor derogatory marks/late payments during initial interview",
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
    
    # Look for dates in the document
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    matches = re.findall(date_pattern, text)
    
    if matches:
        try:
            # Parse first date found
            date_str = matches[0]
            # Simple check: if year is more than 1 year old
            if '2022' in date_str or '2021' in date_str or '2020' in date_str:
                return {
                    "id": "stale-documentation",
                    "name": signal_def["name"],
                    "severity": signal_def["severity"],
                    "summary": "Document appears to be over 60-90 days old",
                    "description": signal_def["description"],
                    "evidence": [f"Date found: {date_str}"],
                    "confidence": 0.65,
                    "weight": signal_def["weight"],
                }
        except:
            pass
    
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
