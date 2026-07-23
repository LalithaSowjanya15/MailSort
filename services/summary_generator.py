"""
Hybrid email summarisation engine for MailSort AI.

Attempts Groq LLM API generation first for high-quality synthesized summaries,
dynamic replies, and classification reasons. Falls back gracefully to 
pure-Python Term Frequency (TF) sentence scoring if Groq is unavailable.
"""

import math
import re

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from utils.helpers import logger
from services.groq_service import get_groq_insights

# Module-level stopwords set — avoids reloading from disk on every call
try:
    _stop_words = set(stopwords.words('english'))
except Exception as _e:
    logger.warning(f"Could not load NLTK stopwords for summariser: {_e}. Using empty set.")
    _stop_words = set()

_RE_PUNCT = re.compile(r'[^\w\s]')


def _tokenize_and_filter(text):
    """
    Lowercases text, removes punctuation, tokenizes, and strips stop words
    and single-character tokens.

    Args:
        text (str): Input text.

    Returns:
        list[str]: Filtered word tokens.
    """
    cleaned = _RE_PUNCT.sub(' ', text.lower())
    try:
        tokens = word_tokenize(cleaned)
    except Exception:
        tokens = cleaned.split()
    return [t for t in tokens if t not in _stop_words and len(t) > 1]


def generate_fallback_summary(body, max_sentences=3):
    """
    Generates an extractive rule-based summary by ranking sentences using TF scoring.
    Used exclusively as a backup if Groq API is unavailable.

    Args:
        body (str): Raw email body text.
        max_sentences (int): Maximum number of sentences to include.

    Returns:
        str: Concatenated summary sentences, or empty string if body is empty.
    """
    if not body or not body.strip():
        return ""

    # Split into sentences
    try:
        sentences = sent_tokenize(body)
    except Exception as e:
        logger.error(f"Sentence tokenisation failed: {e}. Splitting by newline.")
        sentences = [s.strip() for s in body.split('\n') if s.strip()]

    if len(sentences) <= max_sentences:
        return " ".join(s.strip() for s in sentences)

    # Build word frequency table from the entire body
    all_words = _tokenize_and_filter(body)
    if not all_words:
        return " ".join(s.strip() for s in sentences[:max_sentences])

    word_freq = {}
    for word in all_words:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Score each sentence
    sentence_scores = []
    for idx, sentence in enumerate(sentences):
        sentence_clean = sentence.strip()
        if not sentence_clean:
            continue

        words = _tokenize_and_filter(sentence_clean)
        raw_score = sum(word_freq.get(w, 0) for w in words)

        # Length normalisation — prevents very long sentences from dominating
        word_count = len(words)
        if word_count > 0:
            raw_score /= math.log(word_count + 1)

        sentence_scores.append((idx, sentence_clean, raw_score))

    # Select top-ranked sentences and restore original document order
    top = sorted(sentence_scores, key=lambda x: x[2], reverse=True)[:max_sentences]
    top.sort(key=lambda x: x[0])

    return " ".join(s[1] for s in top)


def generate_summary(subject, body):
    """
    Primary interface for summary & reply generation.
    Calls Groq LLM first, using TF extractive scoring as a fallback.

    Args:
        subject (str): Email subject.
        body (str): Raw email body text.

    Returns:
        dict: Keys containing 'summary', 'suggested_reply', and 'reason'.
    """
    fallback_summary = generate_fallback_summary(body)
    fallback_reply = "Thank you for the update. I have received your email and will review the details provided."
    fallback_reason = "General notification requiring review."

    return get_groq_insights(
        subject=subject,
        body=body,
        fallback_summary=fallback_summary,
        fallback_reply=fallback_reply,
        fallback_reason=fallback_reason
    )