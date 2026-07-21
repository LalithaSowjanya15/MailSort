"""
Core email analysis engine for MailSort.
Uses only NLP-based analysis (No Groq, No Sentiment, No Follow-up).
"""

import nltk
from utils.helpers import logger

# Download required NLTK resources
for resource in [
    "punkt",
    "punkt_tab",
    "stopwords",
    "wordnet",
    "omw-1.4",
]:
    try:
        nltk.download(resource, quiet=True)
    except Exception:
        pass

from services.nlp_processor import preprocess_text
from services.deadline_detector import detect_deadline
from services.priority_engine import calculate_priority_and_category
from services.summary_generator import generate_summary


def _build_reply_template(category, sender_name="there"):

    display_name = sender_name

    if "<" in display_name:
        display_name = display_name.split("<")[0].strip()

    display_name = display_name.replace('"', "").strip()

    if not display_name or "@" in display_name:
        display_name = "there"

    templates = {

        "Meeting":
        "Hello,\n\n"
        "Thank you for your email. I am available for the meeting. "
        "Please let me know a suitable time.\n\n"
        "Best regards,",


        "HR":
        "Hello,\n\n"
        "Thank you for the update. I have received your email and will review it.\n\n"
        "Best regards,",


        "Finance":
        "Hello,\n\n"
        "Thank you for sharing the details. I will review them shortly.\n\n"
        "Best regards,",


        "Client":
        f"Hello {display_name},\n\n"
        "Thank you for your email. I have received your request and will respond soon.\n\n"
        "Best regards,",


        "Manager":
        "Hello,\n\n"
        "I have received your request and will complete it as soon as possible.\n\n"
        "Best regards,"
    }

    return templates.get(
        category,
        "Hello,\n\n"
        "Thank you for your email. I have received it and will get back to you soon.\n\n"
        "Best regards,"
    )


def analyze_email(subject, body, email_date=None, sender="Unknown Sender"):

    logger.info(f"NLP analysis started for: '{subject}'")

    cleaned_text, lemmatized_tokens = preprocess_text(subject, body)

    deadline = detect_deadline(
        subject + " " + body,
        base_date=email_date
    )

    priority, priority_score, category, reason = calculate_priority_and_category(
        cleaned_text,
        lemmatized_tokens,
        deadline,
        False
    )

    summary = generate_summary(body)

    suggested_reply = _build_reply_template(category, sender)

    result = {
        "priority": priority,
        "priority_score": priority_score,
        "category": category,
        "summary": summary,
        "deadline": deadline,
        "reason": reason,
        "suggested_reply": suggested_reply,
    }

    logger.info(
        f"NLP analysis complete. Priority={priority}, Category={category}"
    )

    return result