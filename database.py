"""
database.py — Neumann Intelligence
Client registry using SQLite.
Handles: client registration, API key generation, subscription status, custom prompts.
"""

import sqlite3
import secrets
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "./neumannbot.db")

try:
    # Test if we can write to the DB directory
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(db_dir, exist_ok=True)
    test_file = os.path.join(db_dir, "write_test.tmp")
    with open(test_file, "w") as f:
        f.write("ready")
    if os.path.exists(test_file):
        os.remove(test_file)
except Exception as e:
    print(f"⚠️ SQLite permission error at DB directory {db_dir}. Fallback to /tmp/neumannbot.db! Error: {e}")
    DB_PATH = "/tmp/neumannbot.db"


def get_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates all tables if they don't exist.
    Call this once on startup.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Clients table — one row per business
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id TEXT UNIQUE NOT NULL,
            business_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            system_prompt TEXT DEFAULT 'You are a helpful assistant. Answer only from the provided context.',
            bot_name TEXT DEFAULT 'Whisper',
            bot_color TEXT DEFAULT '#6366f1',
            plan TEXT DEFAULT 'free',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # Messages table — persistent analytics (replaces in-memory log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            org_id TEXT NOT NULL,
            message TEXT NOT NULL,
            reply TEXT NOT NULL,
            escalate INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        )
    """)

    # Documents table — track uploaded files per client
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            chunks_stored INTEGER DEFAULT 0,
            uploaded_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")


# ─────────────────────────────────────────────
# CLIENT OPERATIONS
# ─────────────────────────────────────────────

def create_client(business_name: str, email: str) -> dict:
    """
    Registers a new client.
    Auto-generates org_id and api_key.
    Returns the new client record.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Generate unique identifiers
    org_id = "org_" + secrets.token_hex(6)       # e.g. org_a3f9b2
    api_key = "nb_" + secrets.token_urlsafe(32)   # e.g. nb_xyz...

    try:
        cursor.execute("""
            INSERT INTO clients (org_id, business_name, email, api_key, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (org_id, business_name, email, api_key, datetime.now().isoformat()))

        conn.commit()

        return {
            "org_id": org_id,
            "business_name": business_name,
            "email": email,
            "api_key": api_key,
            "bot_name": "Whisper",
            "bot_color": "#6366f1",
            "plan": "free",
            "is_active": True
        }

    except sqlite3.IntegrityError:
        raise ValueError(f"Email '{email}' is already registered.")

    finally:
        conn.close()


def get_client_by_api_key(api_key: str) -> dict | None:
    """
    Looks up a client by their API key.
    Returns client dict or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM clients WHERE api_key = ? AND is_active = 1
    """, (api_key,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_client_by_org_id(org_id: str) -> dict | None:
    """Fetch client details by org_id."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clients WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def update_client_settings(org_id: str, bot_name: str = None,
                           bot_color: str = None, system_prompt: str = None):
    """Updates customization settings for a client."""
    conn = get_connection()
    cursor = conn.cursor()

    if bot_name:
        cursor.execute("UPDATE clients SET bot_name = ? WHERE org_id = ?",
                       (bot_name, org_id))
    if bot_color:
        cursor.execute("UPDATE clients SET bot_color = ? WHERE org_id = ?",
                       (bot_color, org_id))
    if system_prompt:
        cursor.execute("UPDATE clients SET system_prompt = ? WHERE org_id = ?",
                       (system_prompt, org_id))

    conn.commit()
    conn.close()


def update_plan(org_id: str, plan: str):
    """Updates subscription plan: free / starter / growth / pro"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET plan = ? WHERE org_id = ?", (plan, org_id))
    conn.commit()
    conn.close()


def deactivate_client(org_id: str):
    """Deactivates a client (soft delete)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET is_active = 0 WHERE org_id = ?", (org_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# PLAN LIMITS
# ─────────────────────────────────────────────

PLAN_LIMITS = {
    "free":    {"pdfs": 1,  "messages_per_day": 50},
    "starter": {"pdfs": 3,  "messages_per_day": 500},
    "growth":  {"pdfs": 10, "messages_per_day": 2000},
    "pro":     {"pdfs": 999, "messages_per_day": 99999},
}


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def get_document_count(org_id: str) -> int:
    """Returns number of documents uploaded by this org."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM documents WHERE org_id = ?", (org_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def log_document(org_id: str, filename: str, chunks: int):
    """Records a document upload."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (org_id, filename, chunks_stored, uploaded_at)
        VALUES (?, ?, ?, ?)
    """, (org_id, filename, chunks, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_documents(org_id: str) -> list:
    """Returns all documents uploaded by an org."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT filename, chunks_stored, uploaded_at
        FROM documents WHERE org_id = ?
        ORDER BY uploaded_at DESC
    """, (org_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# PERSISTENT ANALYTICS
# ─────────────────────────────────────────────

def log_message_db(session_id: str, org_id: str, message: str,
                   reply: str, escalate: bool):
    """Saves a conversation turn to SQLite (persistent)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (session_id, org_id, message, reply, escalate, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, org_id, message, reply, int(escalate),
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_analytics_db(org_id: str) -> dict:
    """Returns analytics for a specific org from SQLite."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM messages WHERE org_id = ?
        ORDER BY timestamp DESC
    """, (org_id,))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return {
            "org_id": org_id,
            "total_messages": 0,
            "total_conversations": 0,
            "escalations": 0,
            "top_questions": [],
            "recent_questions": []
        }

    unique_sessions = set(r["session_id"] for r in rows)
    escalations = sum(1 for r in rows if r["escalate"])
    recent = [r["message"] for r in rows[:5]]

    question_count = {}
    for r in rows:
        msg = r["message"].lower().strip()
        question_count[msg] = question_count.get(msg, 0) + 1

    top_questions = sorted(
        question_count.items(), key=lambda x: x[1], reverse=True
    )[:5]

    return {
        "org_id": org_id,
        "total_messages": len(rows),
        "total_conversations": len(unique_sessions),
        "escalations": escalations,
        "top_questions": [{"question": q, "count": c} for q, c in top_questions],
        "recent_questions": recent
    }
