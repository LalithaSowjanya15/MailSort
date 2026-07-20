"""
nlp_processor.py
----------------
Text preprocessing pipeline for MailSort's NLP rule engine.

Converts raw email text into a cleaned string and a list of
lemmatized tokens suitable for keyword matching and scoring.
"""

import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from utils.helpers import logger

# Download required NLTK resources once at import time
for _resource in ('punkt', 'punkt_tab', 'stopwords', 'wordnet', 'omw-1.4'):
    try:
        nltk.download(_resource, quiet=True)
    except Exception as _e:
        logger.warning(f"NLTK download failed for '{_resource}': {_e}")

# Module-level singletons — avoids rebuilding these objects on every call
try:
    _stop_words = set(stopwords.words('english'))
except Exception as _e:
    logger.warning(f"Could not load NLTK stopwords: {_e}. Using empty set.")
    _stop_words = set()

try:
    _lemmatizer = WordNetLemmatizer()
except Exception as _e:
    logger.warning(f"Could not initialise WordNetLemmatizer: {_e}.")
    _lemmatizer = None

# Compiled regex patterns for text cleaning
_RE_HTML_COMMENTS  = re.compile(r'<!--.*?-->', re.DOTALL)
_RE_SCRIPT         = re.compile(r'<script.*?>.*?</script>', re.DOTALL | re.IGNORECASE)
_RE_STYLE          = re.compile(r'<style.*?>.*?</style>',  re.DOTALL | re.IGNORECASE)
_RE_HTML_TAGS      = re.compile(r'<[^>]+>')
_RE_PUNCTUATION    = re.compile(r'[^\w\s]')
_RE_DIGITS_UNDER   = re.compile(r'[\d_]+')
_RE_WHITESPACE     = re.compile(r'\s+')


def clean_html(text):
    """Strips HTML comments, scripts, styles, and all remaining tags from text."""
    if not text:
        return ""
    text = _RE_HTML_COMMENTS.sub(' ', text)
    text = _RE_SCRIPT.sub(' ', text)
    text = _RE_STYLE.sub(' ', text)
    text = _RE_HTML_TAGS.sub(' ', text)
    return text


def preprocess_text(subject, body):
    """
    Executes the full NLP preprocessing pipeline on email subject and body.

    Steps:
      1. Combine subject + body into a single string
      2. Lowercase
      3. Strip HTML tags (comments, scripts, styles, elements)
      4. Remove punctuation and symbol characters
      5. Remove digit runs and underscores
      6. Collapse whitespace
      7. Tokenize
      8. Remove English stop words
      9. Lemmatize tokens

    Args:
        subject (str): Email subject line.
        body    (str): Email body (may contain HTML).

    Returns:
        tuple[str, list[str]]:
            - cleaned_text: lowercased, HTML-stripped, punctuation-removed text
            - lemmatized_tokens: filtered and lemmatized word list
    """
    # 1–6: clean pipeline
    combined = f"{subject or ''} {body or ''}"
    no_html   = clean_html(combined.lower())
    no_punct  = _RE_PUNCTUATION.sub(' ', no_html)
    no_digits = _RE_DIGITS_UNDER.sub(' ', no_punct)
    cleaned_text = _RE_WHITESPACE.sub(' ', no_digits).strip()

    # 7. Tokenize
    try:
        tokens = word_tokenize(cleaned_text)
    except Exception as e:
        logger.error(f"Tokenisation failed: {e}. Falling back to str.split().")
        tokens = cleaned_text.split()

    # 8. Remove stop words
    tokens = [t for t in tokens if t not in _stop_words]

    # 9. Lemmatize
    if _lemmatizer:
        try:
            lemmatized_tokens = [_lemmatizer.lemmatize(t) for t in tokens]
        except Exception as e:
            logger.error(f"Lemmatisation failed: {e}. Using raw tokens.")
            lemmatized_tokens = tokens
    else:
        lemmatized_tokens = tokens

    return cleaned_text, lemmatized_tokens
