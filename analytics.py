from datetime import datetime

# In-memory log — stores every message
# Later we'll replace this with PostgreSQL
message_log = []


def log_message(session_id: str, org_id: str, message: str, 
                reply: str, escalate: bool):
    """
    Saves every conversation turn to the log
    """
    message_log.append({
        "session_id": session_id,
        "org_id": org_id,
        "message": message,
        "reply": reply,
        "escalate": escalate,
        "timestamp": datetime.now().isoformat()
    })


def get_analytics(org_id: str):
    """
    Reads the log and returns insights for a specific org
    """

    # Filter logs for this org only
    org_logs = [
        log for log in message_log 
        if log["org_id"] == org_id
    ]

    if not org_logs:
        return {
            "org_id": org_id,
            "total_messages": 0,
            "total_conversations": 0,
            "escalations": 0,
            "top_questions": [],
            "recent_questions": []
        }

    # Count unique sessions = conversations
    unique_sessions = set(log["session_id"] for log in org_logs)

    # Count escalations
    escalations = sum(1 for log in org_logs if log["escalate"])

    # Get top 5 most recent questions
    recent = [log["message"] for log in org_logs[-5:]]

    # Count question frequency
    question_count = {}
    for log in org_logs:
        msg = log["message"].lower().strip()
        question_count[msg] = question_count.get(msg, 0) + 1

    # Sort by frequency
    top_questions = sorted(
        question_count.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return {
        "org_id": org_id,
        "total_messages": len(org_logs),
        "total_conversations": len(unique_sessions),
        "escalations": escalations,
        "top_questions": [
            {"question": q, "count": c} 
            for q, c in top_questions
        ],
        "recent_questions": recent
    }
# Keywords that trigger human handoff
ESCALATION_KEYWORDS = [
    "urgent", "angry", "complaint", "refund",
    "legal", "emergency", "frustrated", "useless",
    "speak to human", "talk to person", "real person"
]

def detect_escalation(message: str) -> bool:
    """
    Returns True if the message needs human handoff
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in ESCALATION_KEYWORDS)