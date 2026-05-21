import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

from forensics import extract_document_text


MONEY_PATTERN = re.compile(
    r"(?P<currency>[$₹€£])?\\s*(?P<amount>-?\\d[\\d,]*(?:\\.\\d{1,2})?)"
)

INCOME_HINTS = (
    "income",
    "revenue",
    "salary",
    "gross",
    "earning",
    "credit",
    "deposit",
    "payroll",
    "wage",
    "compensation",
    "bonus",
)
EXPENSE_HINTS = (
    "deduction",
    "expense",
    "tax",
    "liability",
    "cost",
    "fee",
    "debit",
    "withdrawal",
    "payment",
    "charge",
    "insurance",
    "pension",
    "contribution",
)
NET_HINTS = ("net", "total", "balance", "payable", "receivable", "net pay", "take home")

# Payslip-specific fields
PAYSLIP_HINTS = (
    "payslip", "pay slip", "pay stub", "salary slip", "wage slip",
    "employee", "employer", "national insurance", "ni number",
    "tax code", "gross pay", "net pay", "pay period", "pay date",
    "basic salary", "overtime", "allowance",
)

# Bank statement-specific fields
BANK_STATEMENT_HINTS = (
    "statement", "account number", "sort code", "routing",
    "opening balance", "closing balance", "account summary",
    "transaction history", "branch", "iban", "swift", "bic",
)

# Weekend/holiday patterns for backdated transaction detection
WEEKEND_DAYS = {5, 6}  # Saturday, Sunday

# Common date patterns in financial documents
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
        from pypdf import PdfReader
    except ImportError:
        return "", None, ["PDF text extraction unavailable: install pypdf in the backend environment."]

    try:
        reader = PdfReader(io.BytesIO(document_bytes))
        page_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(part.strip() for part in page_text if part.strip())
        confidence = 100.0 if text else 0.0
        return text, confidence, []
    except Exception as exc:
        return "", None, [f"PDF text extraction failed: {exc}"]


def _extract_image_text(document_bytes: bytes) -> Tuple[str, float | None, List[str]]:
    try:
        import pytesseract
    except ImportError:
        return "", None, ["Image OCR unavailable: install pytesseract and Tesseract OCR locally."]

    try:
        image = Image.open(io.BytesIO(document_bytes)).convert("RGB")
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception as exc:
        return "", None, [f"Image OCR failed: {exc}"]

    line_words: Dict[Tuple[int, int, int], List[str]] = {}
    confidences: List[float] = []
    rows = zip(
        ocr_data.get("text", []),
        ocr_data.get("conf", []),
        ocr_data.get("block_num", []),
        ocr_data.get("par_num", []),
        ocr_data.get("line_num", []),
    )
    for text, confidence, block_num, par_num, line_num in rows:
        cleaned = str(text).strip()
        if cleaned:
            line_key = (int(block_num), int(par_num), int(line_num))
            line_words.setdefault(line_key, []).append(cleaned)
        try:
            numeric_confidence = float(confidence)
        except (TypeError, ValueError):
            continue
        if numeric_confidence >= 0:
            confidences.append(numeric_confidence)

    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    extracted_lines = [" ".join(words) for _, words in sorted(line_words.items())]
    return "\n".join(extracted_lines), average_confidence, []


def extract_text_and_numbers(document_bytes: bytes, file_name: str, content_type: str = "") -> Dict[str, Any]:
    """
    Extract text from the uploaded document using local parsers only.
    No remote OCR service or fixed sample payload is used.
    """
    parsed = extract_document_text(document_bytes, file_name, content_type)
    if parsed.get("source") not in {"generic_text_scan"}:
        return {
            "text": parsed.get("text", ""),
            "confidence_score": parsed.get("confidence_score"),
            "source": parsed.get("source"),
            "notes": parsed.get("notes", []),
        }

    if _is_pdf(file_name, document_bytes):
        text, confidence, notes = _extract_pdf_text(document_bytes)
        source = "local_pdf_parser"
    else:
        text, confidence, notes = _extract_image_text(document_bytes)
        source = "local_image_ocr"

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
    """Extract date objects from extracted text for weekend/holiday checks."""
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


# ──────────────────────────────────────────────────────────────────────
# Bank Statement Fraud Detection
# ──────────────────────────────────────────────────────────────────────

def detect_rounded_deposits(financial_values: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Detect perfectly rounded or repeated deposit amounts — a major red flag."""
    anomalies: List[str] = []
    checks: List[str] = []

    income_values = [item for item in financial_values if item["role"] == "income"]
    if len(income_values) < 2:
        return anomalies, checks

    amounts = [item["amount"] for item in income_values]
    checks.append(f"Checked {len(amounts)} income/deposit entries for rounding patterns.")

    # Check for perfectly rounded amounts (multiples of 100 or 1000)
    rounded_count = sum(1 for a in amounts if a > 0 and a == int(a) and int(a) % 100 == 0)
    if rounded_count >= 2 and rounded_count / len(amounts) >= 0.6:
        anomalies.append(
            f"Suspicious rounding: {rounded_count} of {len(amounts)} income entries are perfectly "
            f"rounded to the nearest hundred (e.g., {amounts[0]:,.0f}). "
            "Genuine payroll deposits typically include cents."
        )

    # Check for identical repeated deposits
    counter = Counter(amounts)
    for amount, count in counter.most_common(3):
        if count >= 3 and amount > 0:
            anomalies.append(
                f"Repeated identical deposit: {amount:,.2f} appears {count} times. "
                "Real salary payments usually vary slightly month to month due to taxes, "
                "bonuses, or overtime."
            )
            break

    return anomalies, checks


def detect_balance_inconsistencies(text: str, financial_values: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Check if running balances add up correctly after each transaction."""
    anomalies: List[str] = []
    checks: List[str] = []

    # Look for opening and closing balance patterns
    lower_text = text.lower()
    opening_match = re.search(r"opening\s+balance[:\s]*[$₹€£]?\s*([\d,]+\.?\d*)", lower_text)
    closing_match = re.search(r"closing\s+balance[:\s]*[$₹€£]?\s*([\d,]+\.?\d*)", lower_text)

    if opening_match and closing_match:
        try:
            opening = float(opening_match.group(1).replace(",", ""))
            closing = float(closing_match.group(1).replace(",", ""))
            checks.append(f"Found opening balance ({opening:,.2f}) and closing balance ({closing:,.2f}).")

            # Sum all credits and debits
            total_credits = sum(
                item["amount"] for item in financial_values
                if item["role"] == "income" and item["amount"] > 0
            )
            total_debits = sum(
                item["amount"] for item in financial_values
                if item["role"] == "expense" and item["amount"] > 0
            )

            expected_closing = opening + total_credits - total_debits
            tolerance = max(1.0, abs(expected_closing) * 0.02)

            if abs(expected_closing - closing) > tolerance:
                anomalies.append(
                    f"Balance inconsistency: opening ({opening:,.2f}) + credits ({total_credits:,.2f}) "
                    f"- debits ({total_debits:,.2f}) = {expected_closing:,.2f}, but closing balance "
                    f"shows {closing:,.2f}. This is a strong indicator of statement manipulation."
                )
        except ValueError:
            pass

    return anomalies, checks


def detect_missing_standard_expenses(text: str) -> Tuple[List[str], List[str]]:
    """Flag statements with deposits but no typical living expenses."""
    anomalies: List[str] = []
    checks: List[str] = []

    lower_text = text.lower()
    has_deposits = bool(re.search(r"(deposit|credit|salary|income|payroll)", lower_text))
    if not has_deposits:
        return anomalies, checks

    # Check for standard monthly expenses that real accounts have
    standard_expenses = {
        "utilities": ("utility", "electric", "gas", "water", "power", "energy"),
        "groceries": ("grocery", "supermarket", "walmart", "tesco", "aldi", "lidl", "costco"),
        "rent/mortgage": ("rent", "mortgage", "housing", "lease"),
        "phone/internet": ("phone", "mobile", "internet", "broadband", "telecom", "verizon", "at&t"),
        "insurance": ("insurance", "premium", "coverage"),
        "subscriptions": ("subscription", "netflix", "spotify", "amazon", "membership"),
    }

    found_categories: List[str] = []
    missing_categories: List[str] = []

    for category, keywords in standard_expenses.items():
        if any(kw in lower_text for kw in keywords):
            found_categories.append(category)
        else:
            missing_categories.append(category)

    checks.append(
        f"Expense category scan: found {len(found_categories)} of {len(standard_expenses)} "
        f"standard categories ({', '.join(found_categories) or 'none'})."
    )

    if len(missing_categories) >= 5 and has_deposits:
        anomalies.append(
            f"Suspicious activity pattern: statement shows deposits but is missing all "
            f"standard living expenses ({', '.join(missing_categories[:4])}...). "
            "Real personal accounts show regular spending on utilities, groceries, and other necessities."
        )

    return anomalies, checks


def detect_weekend_transactions(text: str) -> Tuple[List[str], List[str]]:
    """Flag transactions backdated to weekends or known holidays."""
    anomalies: List[str] = []
    checks: List[str] = []

    dates = _parse_dates_from_text(text)
    if not dates:
        return anomalies, checks

    checks.append(f"Parsed {len(dates)} date(s) from document text for weekend/holiday checks.")

    weekend_dates = [d for d in dates if d.weekday() in WEEKEND_DAYS]
    if len(weekend_dates) >= 3:
        formatted = [d.strftime("%Y-%m-%d (%A)") for d in weekend_dates[:4]]
        anomalies.append(
            f"Backdated transactions: {len(weekend_dates)} transaction dates fall on weekends "
            f"({', '.join(formatted)}). Most bank processing does not occur on Saturdays or Sundays."
        )

    return anomalies, checks


def detect_vague_descriptions(text: str) -> Tuple[List[str], List[str]]:
    """Flag deposits with vague descriptions instead of specific employer names."""
    anomalies: List[str] = []
    checks: List[str] = []

    lower_text = text.lower()
    vague_patterns = [
        r"\b(credit|incoming\s+transfer|funds?\s+transfer|bank\s+transfer|payment\s+received)\b",
    ]
    specific_patterns = [
        r"\b(payroll|salary\s+from|wages?\s+from|company|ltd|inc|corp|llc|plc)\b",
    ]

    vague_count = 0
    specific_count = 0
    for pattern in vague_patterns:
        vague_count += len(re.findall(pattern, lower_text))
    for pattern in specific_patterns:
        specific_count += len(re.findall(pattern, lower_text))

    if vague_count >= 3 and specific_count == 0:
        checks.append(f"Found {vague_count} vague deposit descriptions and {specific_count} specific employer references.")
        anomalies.append(
            f"Vague deposit descriptions: {vague_count} deposits labeled generically as 'credit' "
            "or 'incoming transfer' without any identifiable employer or payroll reference. "
            "Legitimate bank statements typically show the employer name in salary credits."
        )

    return anomalies, checks


# ──────────────────────────────────────────────────────────────────────
# Payslip Fraud Detection
# ──────────────────────────────────────────────────────────────────────

def detect_payslip_anomalies(text: str, financial_values: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Detect common payslip fraud indicators."""
    anomalies: List[str] = []
    checks: List[str] = []

    lower_text = text.lower()
    is_payslip = any(hint in lower_text for hint in PAYSLIP_HINTS)
    if not is_payslip:
        return anomalies, checks

    checks.append("Document detected as payslip — running payslip-specific fraud checks.")

    # Check gross vs net consistency
    gross_values = [
        item["amount"] for item in financial_values
        if "gross" in item["label"].lower() and item["amount"] > 0
    ]
    net_values = [
        item["amount"] for item in financial_values
        if any(h in item["label"].lower() for h in ("net pay", "net", "take home")) and item["amount"] > 0
    ]

    if gross_values and net_values:
        gross = gross_values[0]
        net = net_values[0]
        checks.append(f"Gross pay: {gross:,.2f}, Net pay: {net:,.2f}.")

        if net > gross:
            anomalies.append(
                f"Net pay ({net:,.2f}) exceeds gross pay ({gross:,.2f}). "
                "This is mathematically impossible and indicates the payslip has been tampered with."
            )

        # Deduction ratio check: typical deductions are 20-45% of gross
        deduction_ratio = (gross - net) / gross if gross > 0 else 0
        if deduction_ratio < 0.10 and gross > 1000:
            anomalies.append(
                f"Unusually low deductions: only {deduction_ratio:.0%} of gross pay deducted. "
                "Typical payslips show 20-45% in taxes, insurance, and pension contributions. "
                "Very low deductions suggest the net amount was manually inflated."
            )
        elif deduction_ratio > 0.65:
            anomalies.append(
                f"Unusually high deductions: {deduction_ratio:.0%} of gross pay deducted. "
                "This exceeds normal ranges and may indicate the gross was inflated to appear "
                "as a higher earner."
            )

    # Check for missing mandatory payslip fields
    mandatory_fields = {
        "employer name/address": ("employer", "company", "ltd", "inc", "corp", "plc"),
        "employee name": ("employee", "name"),
        "tax code/deductions": ("tax", "paye", "tax code", "income tax"),
        "national insurance/social security": ("national insurance", "ni ", "social security", "fica"),
        "pay period": ("pay period", "period", "pay date", "payment date"),
    }

    found_fields: List[str] = []
    missing_fields: List[str] = []
    for field, keywords in mandatory_fields.items():
        if any(kw in lower_text for kw in keywords):
            found_fields.append(field)
        else:
            missing_fields.append(field)

    checks.append(f"Payslip field check: found {len(found_fields)}/{len(mandatory_fields)} mandatory fields.")

    if len(missing_fields) >= 3:
        anomalies.append(
            f"Missing mandatory payslip fields: {', '.join(missing_fields)}. "
            "Legitimate payslips must include employer details, tax information, and payment period. "
            "Missing fields suggest the document may have been fabricated from a template."
        )

    # Check for round salary amounts
    salary_amounts = [item["amount"] for item in financial_values if item["role"] == "income" and item["amount"] > 500]
    for amount in salary_amounts:
        if amount == int(amount) and int(amount) % 1000 == 0:
            anomalies.append(
                f"Perfectly rounded salary: {amount:,.0f}. Real salary calculations with tax, "
                "pension, and insurance deductions almost never produce perfectly rounded figures."
            )
            break

    return anomalies, checks


# ──────────────────────────────────────────────────────────────────────
# Account Detail Consistency
# ──────────────────────────────────────────────────────────────────────

def detect_account_inconsistencies(text: str) -> Tuple[List[str], List[str]]:
    """Check for inconsistent account numbers or details across the document."""
    anomalies: List[str] = []
    checks: List[str] = []

    # Extract all account number patterns
    account_patterns = re.findall(r"(?:account|a/c|acct)[:\s#]*(\d{6,14})", text, re.IGNORECASE)
    if len(account_patterns) >= 2:
        unique_accounts = set(account_patterns)
        checks.append(f"Found {len(account_patterns)} account number references ({len(unique_accounts)} unique).")
        if len(unique_accounts) > 1:
            anomalies.append(
                f"Inconsistent account numbers: found {len(unique_accounts)} different account numbers "
                f"within the same document ({', '.join(list(unique_accounts)[:3])}). "
                "A genuine statement references only one account number consistently."
            )

    # Check sort code / routing consistency
    sort_codes = re.findall(r"(?:sort\s*code|routing)[:\s]*(\d{2}[\s-]?\d{2}[\s-]?\d{2,4})", text, re.IGNORECASE)
    if len(sort_codes) >= 2:
        normalized = [re.sub(r"[\s-]", "", sc) for sc in sort_codes]
        unique_sorts = set(normalized)
        if len(unique_sorts) > 1:
            anomalies.append(
                f"Inconsistent sort/routing codes: {len(unique_sorts)} different codes found. "
                "A single bank statement should reference only one branch code."
            )

    return anomalies, checks


# ──────────────────────────────────────────────────────────────────────
# Document Type Detection
# ──────────────────────────────────────────────────────────────────────

def detect_document_type(text: str) -> str:
    """Classify the document as bank_statement, payslip, or unknown."""
    lower_text = text.lower()
    bank_score = sum(1 for hint in BANK_STATEMENT_HINTS if hint in lower_text)
    payslip_score = sum(1 for hint in PAYSLIP_HINTS if hint in lower_text)

    if payslip_score >= 3:
        return "payslip"
    if bank_score >= 3:
        return "bank_statement"
    if payslip_score > bank_score:
        return "payslip"
    if bank_score > 0:
        return "bank_statement"
    return "unknown"


# ──────────────────────────────────────────────────────────────────────
# Original Math Consistency + Orchestration
# ──────────────────────────────────────────────────────────────────────

def validate_math_consistency(ocr_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate common financial structures from actual extracted text.
    The check runs only when enough labeled amounts are present.
    """
    extracted_text = ocr_data.get("text", "")
    financial_values = _extract_financial_values(extracted_text)
    checks: List[str] = []
    anomalies: List[str] = []

    incomes = [item for item in financial_values if item["role"] == "income"]
    expenses = [item for item in financial_values if item["role"] == "expense"]
    net_values = [item for item in financial_values if item["role"] == "net"]

    if not financial_values:
        checks.append("No labeled monetary values were available for math validation.")
        return True, anomalies, checks

    checks.append(f"Parsed {len(financial_values)} monetary value(s) from extracted text.")

    if not incomes or not net_values:
        checks.append("Not enough income/net fields were present for consistency validation.")
        return True, anomalies, checks

    expected_net = sum(item["amount"] for item in incomes) - sum(item["amount"] for item in expenses)
    stated_net = net_values[-1]["amount"]
    tolerance = max(1.0, abs(expected_net) * 0.01)
    difference = abs(expected_net - stated_net)

    checks.append(
        f"Compared stated net {stated_net:.2f} against computed net {expected_net:.2f}."
    )
    if difference > tolerance:
        anomalies.append(
            "Local math validation: stated net amount does not match parsed income and deduction fields "
            f"(expected {expected_net:.2f}, found {stated_net:.2f})."
        )
        return False, anomalies, checks

    return True, anomalies, checks


def run_advanced_fraud_checks(extracted_text: str) -> Tuple[List[str], List[str]]:
    """
    Run all advanced bank statement and payslip fraud detection checks.
    Returns (anomalies, checks).
    """
    all_anomalies: List[str] = []
    all_checks: List[str] = []

    if not extracted_text or len(extracted_text.strip()) < 20:
        return all_anomalies, all_checks

    doc_type = detect_document_type(extracted_text)
    all_checks.append(f"Document classified as: {doc_type}.")

    financial_values = _extract_financial_values(extracted_text)

    # --- Bank Statement Checks ---
    anomalies, checks = detect_rounded_deposits(financial_values)
    all_anomalies.extend(anomalies)
    all_checks.extend(checks)

    anomalies, checks = detect_balance_inconsistencies(extracted_text, financial_values)
    all_anomalies.extend(anomalies)
    all_checks.extend(checks)

    anomalies, checks = detect_missing_standard_expenses(extracted_text)
    all_anomalies.extend(anomalies)
    all_checks.extend(checks)

    anomalies, checks = detect_weekend_transactions(extracted_text)
    all_anomalies.extend(anomalies)
    all_checks.extend(checks)

    anomalies, checks = detect_vague_descriptions(extracted_text)
    all_anomalies.extend(anomalies)
    all_checks.extend(checks)

    anomalies, checks = detect_account_inconsistencies(extracted_text)
    all_anomalies.extend(anomalies)
    all_checks.extend(checks)

    # --- Payslip Checks ---
    anomalies, checks = detect_payslip_anomalies(extracted_text, financial_values)
    all_anomalies.extend(anomalies)
    all_checks.extend(checks)

    return all_anomalies, all_checks


def run_local_validation(document_bytes: bytes, file_name: str, content_type: str = "") -> Tuple[Dict[str, Any], List[str]]:
    """
    Run local validation over the uploaded document.
    Includes math consistency checks and advanced bank statement / payslip fraud detection.
    """
    ocr_data = extract_text_and_numbers(document_bytes, Path(file_name or "").name, content_type)
    extracted_text = ocr_data.get("text", "")
    notes = list(ocr_data.get("notes", []))

    math_valid, math_anomalies, validation_checks = validate_math_consistency(ocr_data)

    # Run advanced fraud detection checks on extracted text
    advanced_anomalies, advanced_checks = run_advanced_fraud_checks(extracted_text)
    math_anomalies.extend(advanced_anomalies)
    validation_checks.extend(advanced_checks)

    if extracted_text:
        status = "Local validation completed from extracted document text."
    elif notes:
        status = "Local validation completed with limited text extraction."
    else:
        status = "Local validation completed; no machine-readable text was found."

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
