"""
Financial Transaction Validator
Validates that transactions mathematically match statement balances
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


def extract_financial_amounts(text: str) -> list[Decimal]:
    """Extract all financial amounts from text."""
    # Pattern to match currency amounts
    patterns = [
        r'[\$£€¥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[\$£€¥]',  # 1,234.56$
        r'(\d{1,3}(?:,\d{3})*\.\d{2})',  # 1,234.56
    ]
    
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Remove commas and convert to Decimal
                clean_amount = match.replace(',', '')
                amount = Decimal(clean_amount)
                amounts.append(amount)
            except (InvalidOperation, ValueError):
                continue
    
    return amounts


def validate_bank_statement_math(text: str) -> dict[str, Any]:
    """
    Validate that bank statement transactions add up correctly.
    Returns fraud indicators if math doesn't match.
    """
    
    # Extract all amounts
    amounts = extract_financial_amounts(text)
    
    if len(amounts) < 3:
        return {
            "validated": False,
            "reason": "Insufficient financial data to validate",
            "amounts_found": len(amounts),
        }
    
    # Try to identify opening balance, closing balance, and transactions
    # Common patterns in bank statements
    
    # Look for balance keywords
    opening_balance = _find_balance(text, ["opening balance", "previous balance", "balance brought forward", "b/f"])
    closing_balance = _find_balance(text, ["closing balance", "current balance", "balance carried forward", "c/f", "ending balance"])
    
    # Extract transactions (credits and debits)
    credits = _extract_transactions(text, ["credit", "deposit", "cr", "paid in"])
    debits = _extract_transactions(text, ["debit", "withdrawal", "dr", "paid out"])
    
    # Validate the math
    validation_results = []
    
    if opening_balance and closing_balance:
        # Calculate expected closing balance
        total_credits = sum(credits) if credits else Decimal('0')
        total_debits = sum(debits) if debits else Decimal('0')
        
        calculated_closing = opening_balance + total_credits - total_debits
        
        # Allow small rounding differences (0.02)
        difference = abs(calculated_closing - closing_balance)
        
        if difference > Decimal('0.02'):
            validation_results.append({
                "type": "balance_mismatch",
                "severity": "high",
                "description": f"Closing balance doesn't match calculations",
                "opening_balance": float(opening_balance),
                "closing_balance": float(closing_balance),
                "calculated_closing": float(calculated_closing),
                "difference": float(difference),
                "total_credits": float(total_credits),
                "total_debits": float(total_debits),
            })
    
    # Check for suspicious patterns
    
    # 1. Identical amounts (fraud indicator)
    if amounts:
        from collections import Counter
        amount_counts = Counter(amounts)
        identical_amounts = [amt for amt, count in amount_counts.items() if count >= 3]
        
        if identical_amounts:
            validation_results.append({
                "type": "identical_amounts",
                "severity": "high",
                "description": f"Found {len(identical_amounts)} amounts repeated 3+ times",
                "identical_amounts": [float(amt) for amt in identical_amounts[:5]],
            })
    
    # 2. Round numbers (fraud indicator)
    round_amounts = [amt for amt in amounts if amt == amt.quantize(Decimal('1'))]
    round_percentage = (len(round_amounts) / len(amounts)) * 100 if amounts else 0
    
    if round_percentage > 70:
        validation_results.append({
            "type": "excessive_round_numbers",
            "severity": "high",
            "description": f"{round_percentage:.1f}% of amounts are perfectly rounded",
            "round_percentage": round(round_percentage, 1),
            "round_count": len(round_amounts),
            "total_count": len(amounts),
        })
    
    # 3. Very round numbers (1000, 5000, etc.)
    very_round = [amt for amt in amounts if amt in [Decimal('1000'), Decimal('2000'), Decimal('3000'), Decimal('5000'), Decimal('10000')]]
    
    if len(very_round) >= 3:
        validation_results.append({
            "type": "very_round_numbers",
            "severity": "medium",
            "description": f"Found {len(very_round)} suspiciously round amounts (1000, 5000, etc.)",
            "very_round_amounts": [float(amt) for amt in very_round],
        })
    
    # 4. Missing variation (all amounts too similar)
    if len(amounts) >= 5:
        amount_values = [float(amt) for amt in amounts]
        mean_amount = sum(amount_values) / len(amount_values)
        variance = sum((x - mean_amount) ** 2 for x in amount_values) / len(amount_values)
        std_dev = variance ** 0.5
        
        # Low standard deviation indicates lack of variation
        if std_dev < mean_amount * 0.1:  # Less than 10% variation
            validation_results.append({
                "type": "low_variation",
                "severity": "medium",
                "description": "Amounts show suspiciously low variation",
                "std_dev": round(std_dev, 2),
                "mean": round(mean_amount, 2),
            })
    
    return {
        "validated": True,
        "amounts_found": len(amounts),
        "opening_balance": float(opening_balance) if opening_balance else None,
        "closing_balance": float(closing_balance) if closing_balance else None,
        "total_credits": float(sum(credits)) if credits else 0,
        "total_debits": float(sum(debits)) if debits else 0,
        "credit_count": len(credits),
        "debit_count": len(debits),
        "validation_results": validation_results,
        "fraud_indicators_found": len(validation_results),
        "has_balance_mismatch": any(v["type"] == "balance_mismatch" for v in validation_results),
    }


def _find_balance(text: str, keywords: list[str]) -> Decimal | None:
    """Find a balance amount near specific keywords."""
    text_lower = text.lower()
    
    for keyword in keywords:
        # Find keyword position
        pos = text_lower.find(keyword)
        if pos == -1:
            continue
        
        # Look for amount near keyword (within 100 characters)
        context = text[pos:pos+100]
        amounts = extract_financial_amounts(context)
        
        if amounts:
            return amounts[0]  # Return first amount found
    
    return None


def _extract_transactions(text: str, keywords: list[str]) -> list[Decimal]:
    """Extract transaction amounts near specific keywords."""
    text_lower = text.lower()
    transactions = []
    
    for keyword in keywords:
        # Find all occurrences of keyword
        pos = 0
        while True:
            pos = text_lower.find(keyword, pos)
            if pos == -1:
                break
            
            # Look for amount near keyword
            context = text[max(0, pos-50):pos+100]
            amounts = extract_financial_amounts(context)
            
            if amounts:
                transactions.append(amounts[0])
            
            pos += len(keyword)
    
    return transactions


def validate_payslip_math(text: str) -> dict[str, Any]:
    """
    Validate that payslip calculations are correct.
    Net pay should equal gross pay minus deductions.
    """
    
    # Look for payslip-specific keywords
    gross_pay = _find_balance(text, ["gross pay", "gross salary", "total earnings"])
    net_pay = _find_balance(text, ["net pay", "net salary", "take home"])
    
    # Look for deductions
    tax = _find_balance(text, ["tax", "income tax", "paye", "federal tax"])
    ni = _find_balance(text, ["national insurance", "ni", "social security"])
    pension = _find_balance(text, ["pension", "retirement", "401k"])
    
    validation_results = []
    
    if gross_pay and net_pay:
        # Calculate total deductions
        total_deductions = Decimal('0')
        if tax:
            total_deductions += tax
        if ni:
            total_deductions += ni
        if pension:
            total_deductions += pension
        
        # Calculate expected net pay
        calculated_net = gross_pay - total_deductions
        
        # Check if it matches
        difference = abs(calculated_net - net_pay)
        
        if difference > Decimal('0.02'):
            validation_results.append({
                "type": "payslip_math_error",
                "severity": "high",
                "description": "Net pay doesn't match gross pay minus deductions",
                "gross_pay": float(gross_pay),
                "net_pay": float(net_pay),
                "calculated_net": float(calculated_net),
                "difference": float(difference),
                "total_deductions": float(total_deductions),
            })
        
        # Check if net > gross (impossible)
        if net_pay > gross_pay:
            validation_results.append({
                "type": "net_exceeds_gross",
                "severity": "high",
                "description": "Net pay is higher than gross pay (impossible)",
                "gross_pay": float(gross_pay),
                "net_pay": float(net_pay),
            })
        
        # Check if deductions are reasonable (typically 20-45% of gross)
        if total_deductions > 0:
            deduction_percentage = (total_deductions / gross_pay) * 100
            
            if deduction_percentage < 10 or deduction_percentage > 60:
                validation_results.append({
                    "type": "unusual_deduction_rate",
                    "severity": "medium",
                    "description": f"Deduction rate of {deduction_percentage:.1f}% is outside normal range (20-45%)",
                    "deduction_percentage": round(float(deduction_percentage), 1),
                })
    
    return {
        "validated": True,
        "gross_pay": float(gross_pay) if gross_pay else None,
        "net_pay": float(net_pay) if net_pay else None,
        "tax": float(tax) if tax else None,
        "ni": float(ni) if ni else None,
        "pension": float(pension) if pension else None,
        "validation_results": validation_results,
        "fraud_indicators_found": len(validation_results),
    }
