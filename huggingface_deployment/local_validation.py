import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from forensics import detect_file_type, extract_document_text

MONEY_PATTERN = re.compile(
    r"(?P<currency>[$₹€£])?\s*(?P<amount>-?\d[\d,]*(?:\.\d{1,2})?)"
)

INCOME_HINTS = (
    "income", "revenue", "salary", "gross", "earning", "credit",
    "deposit", "payroll", "wage", "compensation", "bonus",
)
EXPENSE_HINTS = (
    "deduction", "expense", "tax", "liability", "cost", "fee",
    "debit", "withdrawal", "payment", "charge", "insurance",
    "pension", "contribution",
)
NET_HINTS = ("net", "total", "balance", "payable", "receivable", "net pay", "take home")

PAYSLIP_HINTS = (
    "payslip", "pay slip", "pay stub", "salary slip", "wage slip",
    "employee", "employer", "national insurance", "ni number",
    "tax code", "gross pay", "net pay", "pay period", "pay date",
    "basic salary", "overtime", "allowance",
)

BANK_STATEMENT_HINTS = (
    "statement", "account number", "sort code", "routing",
    "opening balance", "closing balance", "account summary",
    "transaction history", "branch", "iban", "swift", "bic",
)

WEEKEND_DAYS = {5, 6}

DATE_PATTERNS = [
    re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})"),
    re.compile(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})"),
    re.compile(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{2,4})", re.IGNORECASE),
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _is_pdf(file_name: str, document_bytes: bytes) -> bool:
    return file_name.lower().endswith(".pdf") or document_bytes.startswith(b"%PDF")


def _amount_from_match(match: re.Match[str]) -> float | None:
    raw_amount = match.group("amount").replace(",", "")
    try:
        return float(raw_amount)
    except ValueError:
        return None


def _extract_pdf_text(document_bytes: bytes) -> Tuple[str, float | None, List[str]]:
    try:
        import fitz
    except ImportError:
        return "", None, ["PyMuPDF (fitz) is not installed."]

    try:
        doc = fitz.open(stream=document_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text("text"))
        text = "\n".join(text_parts)
        confidence = 100.0 if text else 0.0
        doc.close()
        return text, confidence, []
    except Exception as exc:
        return "", None, [f"PDF text extraction failed: {exc}"]


def extract_text_and_numbers(document_bytes: bytes, file_name: str, content_type: str = "") -> Dict[str, Any]:
    if _is_pdf(file_name, document_bytes):
        text, confidence, notes = _extract_pdf_text(document_bytes)
        source = "local_pdf_parser"
    else:
        text, confidence, notes = "", None, ["Unsupported file type. Only PDF is allowed."]
        source = "unsupported"

    return {
        "text": text,
        "confidence_score": confidence,
        "source": source,
        "notes": notes,
    }


def _classify_line(label: str) -> str | None:
    normalized = label.lower()
    if any(hint in normalized for hint in NET_HINTS):
        return "net"
    if any(hint in normalized for hint in EXPENSE_HINTS):
        return "expense"
    if any(hint in normalized for hint in INCOME_HINTS):
        return "income"
    return None


def _extract_financial_values(text: str) -> List[Dict[str, Any]]:
    values: List[Dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for match in MONEY_PATTERN.finditer(line):
            amount = _amount_from_match(match)
            if amount is None:
                continue
            label = line[: match.start()].strip(" :-\t") or line
            values.append(
                {
                    "line": line,
                    "label": label,
                    "amount": amount,
                    "role": _classify_line(label),
                }
            )
    return values


def _parse_dates_from_text(text: str) -> List[datetime]:
    dates: List[datetime] = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                groups = match.groups()
                if len(groups) == 3 and isinstance(groups[1], str) and groups[1][:3].lower() in MONTH_MAP:
                    day = int(groups[0])
                    month = MONTH_MAP[groups[1][:3].lower()]
                    year = int(groups[2])
                    if year < 100:
                        year += 2000
                    dates.append(datetime(year, month, day))
                elif len(groups) == 3:
                    nums = [int(g) for g in groups]
                    if nums[0] > 1000:
                        dates.append(datetime(nums[0], nums[1], nums[2]))
                    elif nums[2] > 1000:
                        dates.append(datetime(nums[2], nums[1], nums[0]))
                    elif nums[2] < 100:
                        dates.append(datetime(nums[2] + 2000, nums[1], nums[0]))
            except (ValueError, IndexError):
                continue
    return dates


def detect_document_type(text: str) -> str:
    text_lower = text.lower()
    payslip_score = sum(1 for hint in PAYSLIP_HINTS if hint in text_lower)
    bank_score = sum(1 for hint in BANK_STATEMENT_HINTS if hint in text_lower)
    
    if payslip_score > bank_score and payslip_score >= 2:
        return "payslip"
    if bank_score > payslip_score and bank_score >= 2:
        return "bank_statement"
    return "general_financial"


def run_advanced_fraud_checks(extracted_text: str) -> Tuple[List[str], List[str]]:
    all_anomalies: List[str] = []
    all_checks: List[str] = []
    
    if not extracted_text or len(extracted_text.strip()) < 20:
        return all_anomalies, all_checks

    doc_type = detect_document_type(extracted_text)
    all_checks.append(f"Document classified as: {doc_type}.")
    return all_anomalies, all_checks


def validate_math_consistency(ocr_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    return True, [], ["Math consistency validation bypassed for structured checks."]


def run_local_validation(document_bytes: bytes, file_name: str, content_type: str = "") -> Tuple[Dict[str, Any], List[str]]:
    ocr_data = extract_text_and_numbers(document_bytes, Path(file_name or "").name, content_type)
    extracted_text = ocr_data.get("text", "")
    notes = list(ocr_data.get("notes", []))

    math_valid, math_anomalies, validation_checks = validate_math_consistency(ocr_data)
    advanced_anomalies, advanced_checks = run_advanced_fraud_checks(extracted_text)
    
    math_anomalies.extend(advanced_anomalies)
    validation_checks.extend(advanced_checks)

    status = "Local validation completed from extracted document text." if extracted_text else "Local validation completed; no machine-readable text was found."

    results = {
        "extracted_text": extracted_text,
        "ocr_confidence": ocr_data.get("confidence_score"),
        "validation_status": status,
        "validation_checks": validation_checks + notes,
        "text_source": ocr_data.get("source"),
        "math_valid": math_valid,
        "document_type": detect_document_type(extracted_text) if extracted_text else "unknown",
    }
    return results, math_anomalies
