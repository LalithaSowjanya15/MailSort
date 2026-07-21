"""
Core email analysis orchestrator for MailSort.

Combines NLP sub-modules (preprocessing, deadline detection,
sentiment analysis, priority scoring, and Groq AI summary/reply generation)
into a single callable interface used by the email processing pipeline.
"""

import nltk
from utils.helpers import logger

# Bootstrap all required NLTK resources once at import time.
# Each download is idempotent — NLTK skips already-present resources.
_NLTK_RESOURCES = [
    'punkt',
    'punkt_tab',
    'stopwords',
    'wordnet',
    'omw-1.4',
    'vader_lexicon',
    'averaged_perceptron_tagger',
    'averaged_perceptron_tagger_eng',
]

for _resource in _NLTK_RESOURCES:
    try:
        nltk.download(_resource, quiet=True)
    except Exception as _e:
        logger.warning(f"NLTK download failed for '{_resource}': {_e}")

from services.nlp_processor import preprocess_text
from services.deadline_detector import detect_deadline
from services.sentiment_analyzer import get_sentiment
from services.priority_engine import calculate_priority_and_category
from services.summary_generator import generate_summary


def analyze_email(subject, body, email_date=None, sender="Unknown Sender"):
    """
    Analyzes an email using MailSort NLP rules and Groq AI enrichment.

    Pipeline stages:
      1. Text preprocessing (HTML cleaning, tokenization, lemmatization)
      2. Deadline detection via regex + dateparser
      3. Sentiment classification via VADER
      4. Priority scoring and category classification via keyword rules
      5. Groq AI synthesis (concise 1-2 sentence summary, dynamic reply, and reason)

    Returns a dict with keys:
        priority, priority_score, category, summary, deadline,
        sentiment, reason, suggested_reply
    """
    logger.info(f"NLP analysis started for: '{subject}'")

    # 1. Preprocess: clean HTML, lowercase, tokenize, remove stop words, lemmatize
    cleaned_text, lemmatized_tokens = preprocess_text(subject, body)

    # 2. Detect deadline expressions in the combined subject + body
    deadline = detect_deadline(subject + " " + body, base_date=email_date)

    # 3. VADER sentiment classification
    sentiment = get_sentiment(subject + " " + body)

    # 4. Keyword-rule priority scoring and category classification
    priority, priority_score, category, rule_reason = calculate_priority_and_category(
        cleaned_text,
        lemmatized_tokens,
        deadline,
    )

    # 5. Groq AI generation (summary, suggested reply, and classification reason)
    ai_insights = generate_summary(subject=subject, body=body)

    result = {
        "priority": priority,
        "priority_score": priority_score,
        "category": category,
        "summary": ai_insights.get("summary", subject),
        "deadline": deadline,
        "sentiment": sentiment,
        "reason": ai_insights.get("reason", rule_reason),
        "suggested_reply": ai_insights.get("suggested_reply", "Thank you for reaching out. I have received your email."),
    }

    logger.info(
        f"NLP analysis complete. Priority: {priority} ({priority_score}), Category: {category}"
    )
    return result