"""
Keyword-rule priority scoring and category classification engine.

Scores each email against PRIORITY_KEYWORDS and SPECIAL_WEIGHTS,
normalises the result to 0–100, and maps the score to a priority
level and the best-matching category using CATEGORY_KEYWORDS.
"""

import re
from services.keyword_engine import PRIORITY_KEYWORDS, SPECIAL_WEIGHTS, CATEGORY_KEYWORDS
from utils.helpers import logger

def calculate_priority_and_category(cleaned_text, lemmatized_tokens, deadline, has_action_items):
    """
    Evaluates priority score, priority classification, category, and reason.
    
    1. Evaluates keyword weights from PRIORITY_KEYWORDS against lemmatized tokens.
    2. Evaluates SPECIAL_WEIGHTS against cleaned_text.
    3. Normalizes score between 0 and 100.
    4. Classifies Priority: Urgent, Reply Now, Read Later, Ignore.
    5. Evaluates Category using keyword-based scoring.
    6. Generates a custom human-readable explanation reason.
    """
    # Base score starts at 40 (Neutral / Read Later baseline)
    score = 40
    
    matched_indicators = {
        "urgent": [],
        "reply_now": [],
        "read_later": [],
        "ignore": []
    }
    
    # Token-level matching (to count frequency and apply weights)
    token_set = set(lemmatized_tokens)
    
    # Check priority keywords
    for cat_name, kw_dict in PRIORITY_KEYWORDS.items():
        for kw, weight in kw_dict.items():
            if " " in kw:
                if kw in cleaned_text:
                    score += weight
                    matched_indicators[cat_name].append(kw)
            else:
                if kw in token_set:
                    score += weight
                    matched_indicators[cat_name].append(kw)
                    
    # Substring-level special weights (adds weight for high-value terms)
    for kw, weight in SPECIAL_WEIGHTS.items():
        if kw in cleaned_text:
            score += weight
            
    # Check contextual boosts
    if deadline:
        score += 25
    if has_action_items:
        score += 15
        
    # Clip score to valid range [0, 100]
    priority_score = max(0, min(100, int(score)))
    
    # Classify Priority
    if priority_score >= 75:
        priority = "Urgent"
    elif priority_score >= 50:
        priority = "Reply Now"
    elif priority_score >= 20:
        priority = "Read Later"
    else:
        priority = "Ignore"
        
    # Keyword-based category scoring: phrase matches score 2, single-word matches score 1
    category_scores = {}
    for cat, kw_list in CATEGORY_KEYWORDS.items():
        cat_score = 0
        for kw in kw_list:
            if " " in kw:
                if kw in cleaned_text:
                    cat_score += 2 # Phrases get higher weight
            else:
                if kw in token_set:
                    cat_score += 1
        category_scores[cat] = cat_score
        
    # Get category with highest score
    best_category = "Other"
    highest_cat_score = 0
    for cat, cat_s in category_scores.items():
        if cat_s > highest_cat_score:
            highest_cat_score = cat_s
            best_category = cat
            
    # Override category to Security if high-critical security indicators match
    if "security" in matched_indicators["urgent"] or "unauthorized access" in matched_indicators["urgent"]:
        best_category = "Security"
        
    # Reason generation
    reasons = []
    if deadline:
        reasons.append("detected deadline")
    if "manager" in token_set or "boss" in token_set or "sarah" in token_set:
        reasons.append("manager request")
    if matched_indicators["urgent"]:
        kw_list_str = ", ".join(matched_indicators["urgent"][:2])
        reasons.append(f"urgent keywords ({kw_list_str})")
    if has_action_items:
        reasons.append("immediate action requirement")
        
    if not reasons:
        if priority == "Ignore":
            reasons.append("Promotional or marketing content matches")
        elif priority == "Read Later":
            reasons.append("Informational or news content matches")
        else:
            reasons.append("Neutral keyword matching weights")
            
    # Build reason string (capitalize the first and join the rest)
    reason_parts = [r[0].upper() + r[1:] for r in reasons]
    reason = ", ".join(reason_parts) + "."
    
    return priority, priority_score, best_category, reason
