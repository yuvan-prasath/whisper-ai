"""
analytics.py — Neumann Intelligence
Analytics and escalation detection.
Upgraded: now uses SQLite (persistent) instead of in-memory list.
"""

from database import log_message_db, get_analytics_db

# Keywords that trigger human handoff
ESCALATION_KEYWORDS = [
    "urgent", "angry", "complaint", "refund",
    "legal", "emergency", "frustrated", "useless",
    "speak to human", "talk to person", "real person",
    "cancel", "lawsuit", "terrible", "pathetic"
]


def detect_escalation(message: str) -> bool:
    """Returns True if the message needs human handoff."""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in ESCALATION_KEYWORDS)


def log_message(session_id: str, org_id: str, message: str,
                reply: str, escalate: bool):
    """Saves conversation turn to SQLite database (persistent)."""
    log_message_db(session_id, org_id, message, reply, escalate)


def get_analytics(org_id: str) -> dict:
    """Returns analytics for an org from persistent SQLite."""
    return get_analytics_db(org_id)
