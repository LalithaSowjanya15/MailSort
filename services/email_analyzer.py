"""
Core email analysis orchestrator for MailSort.

Combines NLP sub-modules (preprocessing, deadline detection,
priority scoring, and summary generation)
into a single callable interface used by the email processing pipeline.
"""

import nltk
from utils.helpers import logger

# Download required NLTK resources
_NLTK_RESOURCES = [
    "punkt",
    "punkt_tab",
    "stopwords",
    "wordnet",
    "omw-1.4",
]

for _resource in _NLTK_RESOURCES:
    try:
        nltk.download(_resource, quiet=True)
    except Exception as _e:
        logger.warning(f"NLTK download failed for '{_resource}': {_e}")

from services.nlp_processor import preprocess_text
from services.deadline_detector import detect_deadline
from services.summary_generator import generate_summary
from services.priority_engine import calculate_priority_and_category


def analyze_email(subject, body, email_date=None, sender="Unknown Sender"):
    """
    Analyze an email using MailSort's NLP pipeline.

    Pipeline:
      1. Text preprocessing
      2. Deadline detection
      3. Action-item detection
      4. Priority scoring
      5. Category classification
      6. Summary generation

    Returns:
        priority,
        priority_score,
        category,
        summary,
        deadline,
        reason,
        suggested_reply
    """

    logger.info(f"NLP analysis started for: '{subject}'")

    # Preprocess email
    cleaned_text, lemmatized_tokens = preprocess_text(subject, body)

    # Detect deadline
    deadline = detect_deadline(subject + " " + body, base_date=email_date)

    # Detect action items
    action_keywords = [
        "please",
        "kindly",
        "reply",
        "respond",
        "submit",
        "complete",
        "review",
        "send",
        "approve",
        "action required",
        "required",
        "urgent",
    ]

    has_action_items = any(
        keyword in cleaned_text for keyword in action_keywords
    )

    # Calculate priority and category
    priority, priority_score, category, rule_reason = (
        calculate_priority_and_category(
            cleaned_text,
            lemmatized_tokens,
            deadline,
            has_action_items,
        )
    )

    # Generate summary
    ai_insights = generate_summary(
        subject=subject,
        body=body,
    )

    result = {
        "priority": priority,
        "priority_score": priority_score,
        "category": category,
        "summary": ai_insights.get("summary", subject),
        "deadline": deadline,
        "reason": ai_insights.get("reason", rule_reason),
        "suggested_reply": ai_insights.get(
            "suggested_reply",
            "Thank you for reaching out. I have received your email.",
        ),
    }

    logger.info(
        f"NLP analysis complete. Priority: {priority} ({priority_score}), Category: {category}"
    )

    return result