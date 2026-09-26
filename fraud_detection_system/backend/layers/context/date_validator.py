"""
Date Validator Module
Validates dates found in document text for logical consistency.
Detects:
  - Impossible dates (Feb 31, Apr 31, etc.)
  - Future-dated transactions
  - Inconsistent date format usage within a single document
"""

import re
import calendar
from datetime import datetime, date
from typing import List, Tuple, Optional
from models.domain import AnomalyFeature


def validate_dates(text: str) -> List[AnomalyFeature]:
    """
    Scans document text for date anomalies.
    """
    anomalies = []
    
    # Extract all date strings with their patterns
    date_entries = _extract_all_dates(text)
    
    if not date_entries:
        return anomalies
    
    # --- Check 1: Impossible dates ---
    impossible_dates = []
    for date_str, parsed_date, fmt in date_entries:
        if parsed_date is None:
            # Date string that matched a pattern but couldn't be parsed
            impossible_dates.append(date_str)
    
    if impossible_dates:
        anomalies.append(AnomalyFeature(
            type="Impossible Date Detected",
            description=(
                f"Found {len(impossible_dates)} impossible date(s) in the document: "
                f"{', '.join(impossible_dates[:5])}. "
                "Dates like February 30th or April 31st do not exist and indicate "
                "fabricated or carelessly altered transaction records."
            ),
            risk_level="Critical"
        ))
    
    # --- Check 2: Future-dated transactions ---
    valid_dates = [(s, d, f) for s, d, f in date_entries if d is not None]
    today = date.today()
    future_dates = [(s, d) for s, d, f in valid_dates if d > today]
    
    if future_dates:
        anomalies.append(AnomalyFeature(
            type="Future-Dated Transaction",
            description=(
                f"Found {len(future_dates)} date(s) set in the future: "
                f"{', '.join(s for s, d in future_dates[:5])}. "
                "Bank statements should not contain transactions with future dates."
            ),
            risk_level="High"
        ))
    
    # --- Check 3: Mixed date formats ---
    formats_used = set(f for _, d, f in valid_dates if d is not None)
    if len(formats_used) > 1:
        anomalies.append(AnomalyFeature(
            type="Inconsistent Date Formats",
            description=(
                f"Document uses {len(formats_used)} different date formats: "
                f"{', '.join(formats_used)}. "
                "Auto-generated bank statements consistently use a single date format. "
                "Mixed formats suggest manual entry or content combined from multiple sources."
            ),
            risk_level="Medium"
        ))
    
    return anomalies


def _extract_all_dates(text: str) -> List[Tuple[str, Optional[date], str]]:
    """
    Extracts dates from text and attempts to parse them.
    Returns: List of (original_string, parsed_date_or_None, format_name)
    """
    results = []
    
    # Pattern 1: DD/MM/YYYY or DD-MM-YYYY
    for match in re.finditer(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text):
        date_str = match.group(0)
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        
        # Try DD/MM/YYYY first (most common in Indian/European docs)
        parsed = _try_parse_date(day, month, year)
        if parsed:
            results.append((date_str, parsed, "DD/MM/YYYY"))
        else:
            # Try MM/DD/YYYY (US format)
            parsed = _try_parse_date(month, day, year)
            if parsed:
                results.append((date_str, parsed, "MM/DD/YYYY"))
            else:
                # Both failed — impossible date
                results.append((date_str, None, "INVALID"))
    
    # Pattern 2: YYYY-MM-DD (ISO format)
    for match in re.finditer(r'\b(\d{4})-(\d{2})-(\d{2})\b', text):
        date_str = match.group(0)
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        parsed = _try_parse_date(day, month, year)
        if parsed:
            results.append((date_str, parsed, "YYYY-MM-DD"))
        else:
            results.append((date_str, None, "INVALID"))
    
    # Pattern 3: Month name dates (e.g., "January 15, 2024" or "15 Jan 2024")
    month_names = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
        "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12
    }
    
    # "Jan 15, 2024" or "January 15 2024"
    for match in re.finditer(
        r'\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r')\s+(\d{1,2}),?\s+(\d{4})\b',
        text, re.IGNORECASE
    ):
        date_str = match.group(0)
        month = month_names.get(match.group(1).lower()[:3], 0)
        day = int(match.group(2))
        year = int(match.group(3))
        
        parsed = _try_parse_date(day, month, year)
        if parsed:
            results.append((date_str, parsed, "Month DD, YYYY"))
        else:
            results.append((date_str, None, "INVALID"))
    
    # "15 Jan 2024"
    for match in re.finditer(
        r'\b(\d{1,2})\s+((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r')\s+(\d{4})\b',
        text, re.IGNORECASE
    ):
        date_str = match.group(0)
        day = int(match.group(1))
        month = month_names.get(match.group(2).lower()[:3], 0)
        year = int(match.group(3))
        
        parsed = _try_parse_date(day, month, year)
        if parsed:
            results.append((date_str, parsed, "DD Month YYYY"))
        else:
            results.append((date_str, None, "INVALID"))
    
    return results


def _try_parse_date(day: int, month: int, year: int) -> Optional[date]:
    """Tries to create a valid date, returning None for impossible dates."""
    try:
        if year < 1900 or year > 2100:
            return None
        if month < 1 or month > 12:
            return None
        max_day = calendar.monthrange(year, month)[1]
        if day < 1 or day > max_day:
            return None
        return date(year, month, day)
    except (ValueError, OverflowError):
        return None
