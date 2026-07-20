"""
sentiment_analyzer.py
---------------------
VADER-based sentiment classification for email text.
Classifies text as Positive, Neutral, or Negative.
"""

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from utils.helpers import logger

# Ensure the VADER lexicon is present before instantiation
try:
    nltk.download('vader_lexicon', quiet=True)
except Exception as _e:
    logger.warning(f"Failed to download NLTK vader_lexicon: {_e}")

# Module-level singleton — avoids re-loading the lexicon on every call
_sia = SentimentIntensityAnalyzer()


def get_sentiment(text):
    """
    Classifies the sentiment of the given text using VADER.

    Thresholds (compound score):
      >= +0.05 → Positive
      <= -0.05 → Negative
      otherwise → Neutral

    Args:
        text (str): Raw email text (subject + body recommended).

    Returns:
        str: One of 'Positive', 'Neutral', or 'Negative'.
    """
    if not text:
        return "Neutral"

    try:
        scores = _sia.polarity_scores(text)
        compound = scores.get('compound', 0.0)

        if compound >= 0.05:
            return "Positive"
        if compound <= -0.05:
            return "Negative"
        return "Neutral"
    except Exception as e:
        logger.error(f"VADER sentiment analysis error: {e}")
        return "Neutral"
