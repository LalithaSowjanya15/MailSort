"""
action_extractor.py
-------------------
Extracts action items and follow-up indicators from email body text
using two complementary NLP methods:
  1. Pattern matching — regex phrases that signal instructions ("please X", "must X")
  2. Imperative detection — identifies sentences beginning with a known action verb,
     validated against NLTK POS tags to confirm verb form.
"""

import re
import nltk
from nltk import pos_tag
from nltk.tokenize import sent_tokenize, word_tokenize
from utils.helpers import logger

# Ensure perceptron tagger is downloaded
try:
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    logger.warning(f"Failed to download averaged_perceptron_tagger: {e}")

ACTION_VERBS = {
    'submit', 'review', 'approve', 'reply', 'complete', 'send', 'update', 
    'verify', 'confirm', 'join', 'attend', 'schedule', 'prepare', 
    'upload', 'download', 'pay', 'respond', 'check', 'resolve', 'fix'
}

FOLLOW_UP_PHRASES = [
    r"following up",
    r"kind reminder",
    r"gentle reminder",
    r"waiting for your response",
    r"waiting for response",
    r"have you completed",
    r"pending",
    r"please respond",
    r"please reply",
    r"any updates"
]

def check_follow_up(text):
    """
    Checks if the email body requires follow-up based on standard indicators.
    Returns: Boolean
    """
    if not text:
        return False
    text_lower = text.lower()
    for phrase in FOLLOW_UP_PHRASES:
        if re.search(phrase, text_lower):
            return True
    return False

def extract_action_items(body):
    """
    Analyzes the sentences in the email body to extract specific, key action items.
    Returns: List of action item strings.
    """
    if not body:
        return []
        
    try:
        sentences = sent_tokenize(body)
    except Exception as e:
        logger.error(f"Sent_tokenize failed: {e}. Splitting by newline.")
        sentences = [s.strip() for s in body.split('\n') if s.strip()]
        
    action_items = []
    
    # Action item indicators (regex matches indicating tasks)
    indicators = [
        r"\bplease\s+(\w+)",
        r"\bneed\s+to\s+(\w+)",
        r"\bshould\s+(\w+)",
        r"\bmust\s+(\w+)",
        r"\bhave\s+to\s+(\w+)",
        r"\bcould\s+you\s+(\w+)",
        r"\bwants?\s+you\s+to\s+(\w+)",
        r"\btask:\s+(\w+)",
        r"\bremember\s+to\s+(\w+)",
        r"\bdon't\s+forget\s+to\s+(\w+)"
    ]
    
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if not sentence_clean:
            continue
            
        sentence_lower = sentence_clean.lower()
        matched = False
        
        # Method 1: Check indicators
        for ind in indicators:
            match = re.search(ind, sentence_lower)
            if match:
                verb = match.group(1)
                if verb in ACTION_VERBS:
                    matched = True
                    break
                    
        # Method 2: Check if sentence starts with action verb (imperative)
        if not matched:
            # Tokenize first word
            words = word_tokenize(sentence_clean)
            if words:
                first_word = words[0].lower()
                # Strip punctuation
                first_word = re.sub(r'[^\w]', '', first_word)
                if first_word in ACTION_VERBS:
                    # Verify POS tag is indeed a verb
                    try:
                        tagged = pos_tag([words[0]])
                        if tagged and tagged[0][1] in ['VB', 'VBP']:
                            matched = True
                    except Exception:
                        # Fallback: trust the verb list
                        matched = True
                        
        if matched:
            # Clean sentence for display: remove leading hyphens, bullets, or extra spaces
            cleaned_item = re.sub(r'^[\-\*\•\d\.\s]+', '', sentence_clean)
            cleaned_item = cleaned_item.strip()
            # Capitalize first letter
            if cleaned_item:
                cleaned_item = cleaned_item[0].upper() + cleaned_item[1:]
                if cleaned_item not in action_items:
                    action_items.append(cleaned_item)
                    
        if len(action_items) >= 5:
            break
            
    return action_items
