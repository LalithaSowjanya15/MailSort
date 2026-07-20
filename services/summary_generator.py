"""
summary_generator.py
--------------------
Extractive email summarisation using Term Frequency (TF) scoring.

Selects the most information-dense sentences from the email body
without any external API or language model — pure Python NLP.
"""

import math
import re

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from utils.helpers import logger

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


def generate_summary(body, max_sentences=2):
    """
    Generates an extractive summary by ranking sentences using TF scoring.

    Algorithm:
      1. Split the body into sentences.
      2. Build a word frequency map from all body tokens.
      3. Score each sentence as the sum of its constituent word frequencies,
         normalised by log(word_count + 1) to penalise very long sentences.
      4. Return the top-ranked sentences in their original document order.

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
