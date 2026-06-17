"""
Balance Validator Module
Verifies running balances in bank statement transaction tables.
Extracts tabular data using pdfplumber and checks:
  - Each row's running balance = previous_balance ± transaction_amount
  - Opening balance + sum(credits) - sum(debits) = closing balance
"""

import re
import pdfplumber
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
    Extracts transaction rows from PDF tables.
    Looks for columns containing: date, description, debit/credit, balance.
    """
    rows = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Try to identify column indices
                    header = table[0] if table[0] else []
                    header_lower = [str(h).lower().strip() if h else "" for h in header]
                    
                    # Find relevant columns by header name
                    balance_col = _find_column(header_lower, ["balance", "running balance", "closing", "bal"])
                    debit_col = _find_column(header_lower, ["debit", "withdrawal", "dr", "withdrawals"])
                    credit_col = _find_column(header_lower, ["credit", "deposit", "cr", "deposits"])
                    amount_col = _find_column(header_lower, ["amount", "value", "transaction"])
                    
                    if balance_col is None:
                        continue  # Can't verify without a balance column
                    
                    for row_idx, row in enumerate(table[1:], start=1):
                        if not row or len(row) <= balance_col:
                            continue
                        
                        balance = _parse_amount(row[balance_col])
                        if balance is None:
                            continue
                        
                        debit = _parse_amount(row[debit_col]) if debit_col is not None and debit_col < len(row) else None
                        credit = _parse_amount(row[credit_col]) if credit_col is not None and credit_col < len(row) else None
                        amount = _parse_amount(row[amount_col]) if amount_col is not None and amount_col < len(row) else None
                        
                        rows.append({
                            "page": page_num + 1,
                            "row": row_idx,
                            "balance": balance,
                            "debit": debit,
                            "credit": credit,
                            "amount": amount,
                            "raw": row
                        })
    except Exception:
        pass
    
    return rows


def _check_running_balance(rows: List[Dict[str, Any]]) -> List[str]:
    """
    Verifies that each row's balance = previous_balance - debit + credit.
    Returns a list of error descriptions.
    """
    errors = []
    
    for i in range(1, len(rows)):
        prev = rows[i - 1]
        curr = rows[i]
        
        prev_balance = prev["balance"]
        curr_balance = curr["balance"]
        
        # Try to compute expected balance
        debit = curr.get("debit") or 0
        credit = curr.get("credit") or 0
        
        # If we have both debit and credit info
        if debit > 0 or credit > 0:
            expected = prev_balance - debit + credit
            diff = abs(expected - curr_balance)
            
            # Allow small floating point tolerance
            if diff > 0.01:
                errors.append(
                    f"Row {curr['row']} on page {curr['page']}: "
                    f"expected balance {expected:.2f} but found {curr_balance:.2f} "
                    f"(difference: {diff:.2f})"
                )
        
        # If we only have a single amount column, try both directions
        elif curr.get("amount"):
            amt = curr["amount"]
            expected_debit = prev_balance - amt
            expected_credit = prev_balance + amt
            
            if abs(expected_debit - curr_balance) > 0.01 and abs(expected_credit - curr_balance) > 0.01:
                errors.append(
                    f"Row {curr['row']} on page {curr['page']}: "
                    f"balance {curr_balance:.2f} doesn't follow from previous {prev_balance:.2f} "
                    f"with amount {amt:.2f}"
                )
    
    return errors


def _check_opening_closing(rows: List[Dict[str, Any]]) -> Optional[str]:
    """
    Checks if opening_balance + total_credits - total_debits = closing_balance.
    """
    if len(rows) < 2:
        return None
    
    opening = rows[0]["balance"]
    closing = rows[-1]["balance"]
    
    total_credits = sum(r.get("credit", 0) or 0 for r in rows)
    total_debits = sum(r.get("debit", 0) or 0 for r in rows)
    
    if total_credits == 0 and total_debits == 0:
        return None  # Can't verify without transaction data
    
    expected_closing = opening + total_credits - total_debits
    diff = abs(expected_closing - closing)
    
    if diff > 1.0:  # Allow $1 tolerance for rounding
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
            if keyword in header:
                return idx
    return None


def _parse_amount(value) -> Optional[float]:
    """Parse a monetary value string into a float."""
    if value is None:
        return None
    
    text = str(value).strip()
    if not text:
        return None
    
    # Remove currency symbols and commas
    text = re.sub(r'[₹$€£,\s]', '', text)
    
    # Handle parentheses for negative values: (1234.56) -> -1234.56
    negative = False
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]
        negative = True
    if text.endswith('-') or text.startswith('-'):
        text = text.strip('-')
        negative = True
    
    try:
        amount = float(text)
        return -amount if negative else amount
    except (ValueError, TypeError):
        return None
