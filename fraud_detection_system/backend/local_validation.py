import io
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image


MONEY_PATTERN = re.compile(
    r"(?P<currency>[$₹€£])?\s*(?P<amount>-?\d[\d,]*(?:\.\d{1,2})?)"
)

INCOME_HINTS = (
    "income",
    "revenue",
    "salary",
    "gross",
    "earning",
    "credit",
    "deposit",
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
)
NET_HINTS = ("net", "total", "balance", "payable", "receivable")


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


def extract_text_and_numbers(document_bytes: bytes, file_name: str) -> Dict[str, Any]:
    """
    Extract text from the uploaded document using local parsers only.
    No remote OCR service or fixed sample payload is used.
    """
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


def run_local_validation(document_bytes: bytes, file_name: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Run local validation over the uploaded document.
    Kept as the backend entry point so the current service architecture stays stable.
    """
    ocr_data = extract_text_and_numbers(document_bytes, Path(file_name or "").name)
    extracted_text = ocr_data.get("text", "")
    notes = list(ocr_data.get("notes", []))

    math_valid, math_anomalies, validation_checks = validate_math_consistency(ocr_data)

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
    }

    return results, math_anomalies
