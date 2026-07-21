"""
Shared utilities for the MailSort application.
"""

import logging


# Configure root logger with a consistent format used across all modules.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)


def get_logger(name):
    """Returns a named logger instance."""
    return logging.getLogger(name)


# Shared application logger — imported by all modules.
logger = get_logger("MailSort")
