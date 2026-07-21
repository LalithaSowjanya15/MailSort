"""
Groq LLM integration for MailSort AI.

Provides email-specific generation of:
  - summary         : concise, email-specific synthesized summary
  - suggested_reply : professional reply tailored dynamically to email content
  - reason          : human-readable explanation of why the email was classified
"""

import json
import re
from config import Config
from utils.helpers import logger


def _truncate(text, max_chars=3000):
    """Truncate text to avoid token limit issues."""
    if not text:
        return ""
    return text[:max_chars] + ("..." if len(text) > max_chars else "")


def get_groq_insights(subject, body, fallback_summary="", fallback_reply="", fallback_reason=""):
    """
    Calls Groq API to generate summary, suggested_reply, and reason for an email.
    """
    fallback = {
        "summary": fallback_summary,
        "suggested_reply": fallback_reply,
        "reason": fallback_reason,
    }

    api_key = Config.GROQ_API_KEY
    if not api_key:
        logger.warning("GROQ_API_KEY not set — using rule-based fallback for summary/reply/reason.")
        return fallback

    try:
        from groq import Groq  # lazy import
    except ImportError:
        logger.warning("groq package not installed — using rule-based fallback.")
        return fallback

    # System instruction enforces strict LLM behavior
    system_instruction = (
        "You are an expert executive email assistant. Your job is to analyze incoming emails "
        "and return a JSON response with high-level synthesized insights. Never copy full body "
        "text verbatim, and never use generic canned response templates."
    )

    user_prompt = f"""Analyze the email below and return a valid JSON object with exactly three keys: "summary", "suggested_reply", and "reason".

EMAIL DETAILS:
Subject: {subject}
Body:
{_truncate(body)}

OUTPUT JSON SPECIFICATIONS:
1. "summary":
   - Provide a 1-2 sentence high-level summary explaining the core purpose and actionable details.
   - DO NOT copy and paste verbatim text or full sentences from the email body.
   - DO NOT include greetings ("Dear Students") or sign-offs.

2. "suggested_reply":
   - Write a professional, context-aware reply tailored strictly to this specific email.
   - If it's a workshop/event announcement, write an acknowledgment confirming interest or registration intent.
   - If it's a meeting request, respond regarding scheduling.
   - Write 2-3 natural sentences without generic placeholders like [Your Name] or bracketed text.

3. "reason":
   - Provide a 1-sentence explanation of why this email is relevant and what action is required.
"""

    client = Groq(api_key=api_key)
    # Updated list using current Groq supported production models
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    for model_name in models:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
                model=model_name,
                temperature=0.3,  # Lower temperature prevents hallucination & verbatim copying
                max_tokens=500,
                response_format={"type": "json_object"},  # Enforces strict JSON output natively
            )

            raw_response = chat_completion.choices[0].message.content.strip()

            # Parse JSON directly (supported by Groq's json_object mode)
            parsed = json.loads(raw_response)

            result = {
                "summary": parsed.get("summary", "").strip() or fallback_summary,
                "suggested_reply": parsed.get("suggested_reply", "").strip() or fallback_reply,
                "reason": parsed.get("reason", "").strip() or fallback_reason,
            }

            logger.info(f"Groq insights generated successfully using model {model_name}.")
            return result

        except Exception as e:
            logger.warning(f"Groq API call with model '{model_name}' failed: {e}.")

    logger.error("All Groq model attempts failed. Using rule-based fallback.")
    return fallback