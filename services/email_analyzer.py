"""
Core email analysis orchestrator for MailSort.

Combines all NLP sub-modules (preprocessing, deadline detection,
action extraction, sentiment analysis, priority scoring, and summary
generation) into a single callable interface used by the email
processing pipeline.
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
from services.action_extractor import extract_action_items, check_follow_up
from services.sentiment_analyzer import get_sentiment
from services.priority_engine import calculate_priority_and_category
from services.summary_generator import generate_summary


def _build_reply_template(category, sender_name="there"):
    """
    Returns a professional rule-based reply template for the given email
    category. Templates are static text — no AI or LLM is involved.
    """
    # Extract readable display name from RFC 2822 "Name <email>" format
    display_name = sender_name
    if "<" in display_name:
        display_name = display_name.split("<")[0].strip()
    display_name = display_name.replace('"', '').strip()

    # Fall back to generic greeting when name is unavailable or is an address
    if not display_name or "@" in display_name or display_name == "Unknown Sender":
        display_name = "there"

    templates = {
        "Meeting": (
            "Hello,\n\n"
            "Thank you for reaching out. I would be glad to schedule a meeting. "
            "I am available this week to align. Please let me know what dates and "
            "times work best for you, or send over a calendar invite.\n\n"
            "Best regards,"
        ),
        "Manager": (
            "Hi,\n\n"
            "I have received your request. I am working on the updates now and will "
            "send over the completed files/deliverables as soon as possible.\n\n"
            "Best regards,"
        ),
        "Client": (
            f"Hello {display_name},\n\n"
            "Thank you for the message. We have received your inquiry/proposal request "
            "and are preparing a detailed response. We will get back to you with the "
            "requested information shortly.\n\n"
            "Best regards,"
        ),
        "HR": (
            "Hello HR Team,\n\n"
            "Thank you for the notification. I will review the policy details and make "
            "sure to complete any mandatory training or action items before the deadline.\n\n"
            "Best regards,"
        ),
        "Finance": (
            "Hello,\n\n"
            "Thank you for sending the billing details. I have received the "
            "invoice/receipt and will review the charges for processing.\n\n"
            "Best regards,"
        ),
    }

    return templates.get(
        category,
        (
            "Hello,\n\n"
            "Thank you for your email. I have received your message and will look it over. "
            "I will follow up with you shortly if any action is required.\n\n"
            "Best regards,"
        ),
    )


def analyze_email(subject, body, email_date=None, sender="Unknown Sender"):
    """
    Analyzes an email using the MailSort NLP rule engine.

    Pipeline stages:
      1. Text preprocessing (HTML cleaning, tokenization, lemmatization)
      2. Deadline detection via regex + dateparser
      3. Action item extraction via pattern matching and POS tagging
      4. Follow-up indicator detection
      5. Sentiment classification via VADER
      6. Priority scoring and category classification via keyword rules
      7. Extractive TF-based summary generation
      8. Rule-based reply template selection

    Returns a dict with keys:
        priority, priority_score, category, summary, deadline,
        action_items, follow_up_required, sentiment, reason, suggested_reply
    """

    logger.info(f"NLP analysis started for: '{subject}'")

    # Preprocess email
    cleaned_text, lemmatized_tokens = preprocess_text(subject, body)

    # Detect deadline
    deadline = detect_deadline(subject + " " + body, base_date=email_date)

    # 3. Extract imperative action items from the body
    action_items = extract_action_items(body)

    # 4. Detect follow-up request indicators
    follow_up_required = check_follow_up(subject + " " + body)

    # 5. VADER sentiment classification
    sentiment = get_sentiment(subject + " " + body)

    # 6. Keyword-rule priority scoring and category classification
    has_action_items = len(action_items) > 0
    priority, priority_score, category, reason = calculate_priority_and_category(
        cleaned_text,
        lemmatized_tokens,
        deadline,
        has_action_items,
        follow_up_required,
    )

    # 7. Extractive summary (top-2 sentences by TF score)
    summary = generate_summary(body, max_sentences=2) or subject

    # 8. Rule-based reply template
    suggested_reply = _build_reply_template(category, sender)

    result = {
        "priority": priority,
        "priority_score": priority_score,
        "category": category,
        "summary": ai_insights.get("summary", subject),
        "deadline": deadline,
        "action_items": action_items,
        "follow_up_required": follow_up_required,
        "sentiment": sentiment,
        "reason": reason,
        "suggested_reply": suggested_reply,
    }

    logger.info(
        f"NLP analysis complete. Priority: {priority} ({priority_score}), Category: {category}"
    )

    return result