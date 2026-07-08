"""
Balance Validator Module
Verifies running balances in bank statement transaction tables.
Extracts tabular data using pdfplumber and checks:
  - Each row's running balance = previous_balance ± transaction_amount
  - Opening balance + sum(credits) - sum(debits) = closing balance
Uses Decimal arithmetic to eliminate floating-point rounding errors.
"""

import re
import pdfplumber
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
from models.domain import AnomalyFeature


def validate_running_balances(file_path: str) -> List[AnomalyFeature]:
    """
    Extracts transaction tables from PDF and verifies running balances.
    """
    anomalies = []
    
    if not file_path.lower().endswith('.pdf'):
        return anomalies
    
    try:
        all_rows = _extract_transaction_rows(file_path)
        
        if len(all_rows) < 2:
            return anomalies  # Not enough data to verify
        
        # Try to verify running balances
        balance_errors = _check_running_balance(all_rows)
        
        if balance_errors:
            error_details = "; ".join(balance_errors[:3])
            anomalies.append(AnomalyFeature(
                type="Balance Calculation Error",
                description=(
                    f"Found {len(balance_errors)} mathematical error(s) in running balances. "
                    f"Details: {error_details}. "
                    "Fraudsters often modify transaction amounts without updating the cumulative "
                    "balance on following rows, leaving a mathematical trail."
                ),
                risk_level="Critical"
            ))
        
        # Check opening vs closing balance consistency
        totals_error = _check_opening_closing(all_rows)
        if totals_error:
            anomalies.append(AnomalyFeature(
                type="Opening/Closing Balance Mismatch",
                description=totals_error,
                risk_level="High"
            ))
            
    except Exception as e:
        # Don't flag extraction failures as anomalies — not all PDFs have tables
        pass
    
    return anomalies


def _extract_transaction_rows(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts transaction rows by parsing raw text line-by-line.
    Filters for lines that begin with a Date and end with monetary amounts.
    This bypasses brittle table column extractions which fail on multi-line descriptions.
    """
    rows = []
    
    # Matches DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY, or DD MMM YYYY
    date_pattern = re.compile(r'^\s*(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,4}\s+\d{2,4})')
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # layout=True preserves the visual spacing of columns
                text = page.extract_text(layout=True)
                if not text:
                    continue
                
                for row_idx, line in enumerate(text.split('\n')):
                    if not date_pattern.search(line):
                        continue
                    
                    # Extract all monetary values from the line
                    amounts = _extract_monetary_values_from_line(line)
                    
                    if len(amounts) >= 2:
                        # Typical transaction row: ... [Debit/Credit] [Balance]
                        balance = amounts[-1]
                        amount = amounts[-2]
                        
                        rows.append({
                            "page": page_num + 1,
                            "row": row_idx,
                            "balance": balance,
                            "amount": amount,
                            "raw": line.strip()
                        })
                    elif len(amounts) == 1:
                        # Opening balance row: ... [Balance]
                        rows.append({
                            "page": page_num + 1,
                            "row": row_idx,
                            "balance": amounts[0],
                            "amount": None,
                            "raw": line.strip()
                        })
    except Exception as e:
        pass
    
    return rows

def _extract_monetary_values_from_line(line: str) -> List[Decimal]:
    """Helper to extract and parse all monetary amounts in a line."""
    # Match Western (1,234.50) and Indian lakh (1,23,456.78) formats
    pattern = r'\b(?:\d{1,2}(?:,\d{2})*,\d{3}\.\d{2}|\d{1,3}(?:,\d{3})*\.\d{2}|\d+\.\d{2})\b'
    matches = re.findall(pattern, line)
    
    decimals = []
    for m in matches:
        val = _parse_amount(m)
        if val is not None:
            decimals.append(val)
    return decimals


def _check_running_balance(rows: List[Dict[str, Any]]) -> List[str]:
    """
    Verifies that each row's balance = previous_balance ± amount.
    Because we parse raw text lines, we don't know if the amount is a Debit or Credit
    just from the column position. We mathematically deduce it.
    Uses Decimal arithmetic for exact precision.
    """
    errors = []
    TOLERANCE = Decimal("0.50")
    
    for i in range(1, len(rows)):
        prev = rows[i - 1]
        curr = rows[i]
        
        prev_balance = prev["balance"]
        curr_balance = curr["balance"]
        amt = curr.get("amount")
        
        if amt is None:
            continue
            
        expected_debit = prev_balance - amt
        expected_credit = prev_balance + amt
        
        # Check if the math works in either direction
        diff_debit = abs(expected_debit - curr_balance)
        diff_credit = abs(expected_credit - curr_balance)
        
        if diff_debit <= TOLERANCE:
            # It's a valid debit transaction
            curr["debit"] = amt
            curr["credit"] = Decimal("0")
        elif diff_credit <= TOLERANCE:
            # It's a valid credit transaction
            curr["debit"] = Decimal("0")
            curr["credit"] = amt
        else:
            # Neither direction works — this is a real mathematical anomaly
            errors.append(
                f"Row {curr['row']} on page {curr['page']}: "
                f"balance {curr_balance:.2f} doesn't mathematically follow from previous "
                f"balance {prev_balance:.2f} using transaction amount {amt:.2f}. "
                f"(If Debit: expected {expected_debit:.2f}. If Credit: expected {expected_credit:.2f})"
            )
            
    return errors


def _check_opening_closing(rows: List[Dict[str, Any]]) -> Optional[str]:
    """
    Checks if opening_balance + total_credits - total_debits = closing_balance.
    Excludes the first row from sums since its balance IS the opening balance.
    """
    if len(rows) < 2:
        return None
    
    opening = rows[0]["balance"]
    closing = rows[-1]["balance"]
    
    # Sum credits/debits starting from row index 1 (exclude the opening balance row)
    total_credits = sum((r.get("credit") or Decimal("0")) for r in rows[1:])
    total_debits = sum((r.get("debit") or Decimal("0")) for r in rows[1:])
    
    if total_credits == 0 and total_debits == 0:
        return None  # Can't verify without transaction data
    
    expected_closing = opening + total_credits - total_debits
    diff = abs(expected_closing - closing)
    
    if diff > Decimal("1.0"):  # Allow ₹1 tolerance for rounding
        return (
            f"Opening balance ({opening:.2f}) + credits ({total_credits:.2f}) "
            f"- debits ({total_debits:.2f}) = {expected_closing:.2f}, "
            f"but closing balance shows {closing:.2f} (difference: {diff:.2f}). "
            "This mathematical inconsistency strongly indicates tampering."
        )
    
    return None


def _find_column(headers: List[str], keywords: List[str]) -> Optional[int]:
    """Find a column index by matching header keywords."""
    for idx, header in enumerate(headers):
        for keyword in keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', header):
                return idx
    return None


def _parse_amount(value) -> Optional[Decimal]:
    """Parse a monetary value string into a Decimal.
    Supports both Western (1,234.56) and Indian lakh (1,23,456.78) formats."""
    if value is None:
        return None
    
    text = str(value).strip()
    if not text:
        return None
    
    # Remove currency symbols and whitespace
    text = re.sub(r'[₹$€£\s]', '', text)
    
    # Handle parentheses for negative values: (1234.56) -> -1234.56
    negative = False
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]
        negative = True
    if text.endswith('-') or text.startswith('-'):
        text = text.strip('-')
        negative = True
    
    # Remove all commas (handles both Western and Indian lakh formatting)
    text = text.replace(',', '')
    
    try:
        amount = Decimal(text)
        return -amount if negative else amount
    except (InvalidOperation, ValueError, TypeError):
        return None
