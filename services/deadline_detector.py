"""
deadline_detector.py
--------------------
Detects deadline expressions in email text using regex pattern matching
combined with dateparser for natural-language date resolution.

Returns the first recognised deadline as a formatted date string
(YYYY-MM-DD or YYYY-MM-DD HH:MM), or an empty string if none is found.
"""

import re
import dateparser
from datetime import datetime
from utils.helpers import logger

DEADLINE_PATTERNS = [
    # ISO-like date: 2026-07-25
    r"\b\d{4}-\d{2}-\d{2}\b",
    # Specific date: 15 July, July 15, 15th July, 15 July 2026
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)(?:\s+\d{4})?\b",
    r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?\b",
    # Relative day terms: today, tomorrow
    r"\b(?:today|tomorrow)\b",
    r"\bwithin\s+\d+\s+days?\b",
    r"\bnext\s+week\b",
    # Days of the week: Monday, Friday, etc.
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    # Slash/Dash dates: 07/25/2026, 25-07-2026
    r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b",
    # Time expressions: 5 PM, 2:30 PM
    r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm|am\b|pm\b)\b",
    r"\b\d{1,2}:\d{2}\b"
]

def detect_deadline(text, base_date=None):
    """
    Scans the text using regex to find candidate deadline patterns and
    resolves them using dateparser relative to base_date (datetime).
    Returns: a formatted deadline string, e.g. '2026-07-25' or '2026-07-25 17:00', or empty string.
    """
    if not text:
        return ""
        
    if not base_date:
        base_date = datetime.now()
    elif isinstance(base_date, (int, float)):
        base_date = datetime.fromtimestamp(base_date)
        
    candidates = []
    
    # Run regex search for deadline candidate patterns
    for pattern in DEADLINE_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            candidates.append((match.group(0), match.start()))
            
    # Sort candidates by their position in the text (first mention is primary)
    candidates.sort(key=lambda x: x[1])
    
    # Parse candidates using dateparser
    for val, pos in candidates:
        try:
            cleaned_val = val.lower().strip()
            if "within" in cleaned_val:
                cleaned_val = cleaned_val.replace("within", "in")
                
            parsed_dt = dateparser.parse(
                cleaned_val, 
                settings={'RELATIVE_BASE': base_date, 'PREFER_DATES_FROM': 'future'}
            )
            if parsed_dt:
                # Check if it was a simple time-only format or if it has date
                is_time_only = re.match(r'^\d{1,2}(?::\d{2})?\s*(?:am|pm)?$', val, re.IGNORECASE)
                if is_time_only:
                    return parsed_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    if parsed_dt.hour == 0 and parsed_dt.minute == 0:
                        return parsed_dt.strftime("%Y-%m-%d")
                    else:
                        return parsed_dt.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            logger.debug(f"Dateparser failed to parse candidate '{val}': {e}")
            
    return ""
