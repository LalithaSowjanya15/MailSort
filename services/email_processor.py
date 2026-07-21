"""
Orchestrates the email ingestion, NLP analysis, and MongoDB storage pipeline.

Flow:
  1. Fetch recent raw emails from Gmail API (or mock data in MOCK_MODE).
  2. Skip emails already stored for the current user.
  3. Reuse NLP analysis from existing records when the same message was
     processed for a different user — avoids redundant computation.
  4. Run the NLP analysis pipeline on genuinely new emails.
  5. Persist the fully analysed record in MongoDB.
  6. Return all emails for the user, sorted newest-first.
"""

import time
from database.mongodb import get_db
from services.gmail_service import fetch_gmail_emails
from services.email_analyzer import analyze_email
from utils.helpers import logger


def process_and_sync_emails(user_email, credentials_dict, max_results=15):
    """
    Synchronises and analyses emails for a user, returning the full stored list.

    Args:
        user_email (str): The authenticated user's email address.
        credentials_dict (dict): OAuth credential payload for Gmail API access.
        max_results (int): Maximum number of Gmail messages to fetch per sync.

    Returns:
        list[dict]: All processed email documents for the user, newest first.
    """
    logger.info(f"Starting email sync for user: {user_email}")
    db = get_db()

    # Step 1 — Fetch raw emails from Gmail API (or mock feed)
    raw_emails = fetch_gmail_emails(credentials_dict, user_email=user_email, max_results=max_results)

    new_emails_processed = 0

    for raw in raw_emails:
        gmail_id = raw.get("gmail_id")
        if not gmail_id:
            continue

        # Step 2 — Check whether this message is already stored globally
        existing = db.emails.find_one({"gmail_id": gmail_id})

        if existing:
            if existing.get("user_email") == user_email:
                # Already processed for this user — skip entirely
                logger.info(f"Skipping already-stored email {gmail_id} for {user_email}.")
                continue

            # Step 3 — Reuse NLP analysis from another user's stored record
            logger.info(
                f"Reusing NLP analysis for email {gmail_id} "
                f"(originally processed for {existing.get('user_email')})."
            )
            analysis = {
                "priority":          existing.get("priority",          "Read Later"),
                "priority_score":    existing.get("priority_score",    50),
                "category":          existing.get("category",          "Other"),
                "summary":           existing.get("summary",           ""),
                "deadline":          existing.get("deadline",          ""),
                "action_items":      existing.get("action_items",      []),
                "sentiment":         existing.get("sentiment",         "Neutral"),
                "reason":            existing.get("reason",            ""),
                "suggested_reply":   existing.get("suggested_reply",   ""),
            }
        else:
            # Step 4 — Run the full NLP analysis pipeline on a new email
            analysis = analyze_email(
                raw.get("subject", ""),
                raw.get("body", ""),
                email_date=raw.get("created_at"),
                sender=raw.get("sender", "Unknown Sender"),
            )

        # Step 5 — Persist the fully analysed record
        processed_record = {
            "gmail_id":          gmail_id,
            "thread_id":         raw.get("thread_id"),
            "user_email":        user_email,
            "sender":            raw.get("sender"),
            "receiver":          raw.get("receiver"),
            "subject":           raw.get("subject"),
            "body":              raw.get("body"),
            "date":              raw.get("date"),
            "attachments":       raw.get("attachments", []),
            "priority":          analysis.get("priority",          "Read Later"),
            "priority_score":    analysis.get("priority_score",    50),
            "category":          analysis.get("category",          "Other"),
            "summary":           analysis.get("summary",           ""),
            "deadline":          analysis.get("deadline",          ""),
            "action_items":      analysis.get("action_items",      []),
            "sentiment":         analysis.get("sentiment",         "Neutral"),
            "reason":            analysis.get("reason",            ""),
            "suggested_reply":   analysis.get("suggested_reply",   ""),
            "status":            "unread",
            "created_at":        raw.get("created_at", time.time()),
        }

        db.emails.insert_one(processed_record)
        new_emails_processed += 1

    logger.info(f"Email sync complete. {new_emails_processed} new email(s) processed for {user_email}.")

    # Step 6 — Return all stored emails for this user, newest first
    return list(db.emails.find({"user_email": user_email}).sort("created_at", -1))
