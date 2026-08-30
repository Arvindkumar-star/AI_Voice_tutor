import sqlite3
from datetime import datetime
from app.services.gemini_client import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            language TEXT NOT NULL,
            original_text TEXT NOT NULL,
            corrected_text TEXT NOT NULL,
            feedback TEXT NOT NULL,
            had_errors INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_attempt(username: str, language: str, original_text: str,
                  corrected_text: str, feedback: str, had_errors: bool):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO attempts (username, language, original_text, corrected_text, feedback, had_errors, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (username, language, original_text, corrected_text, feedback,
         int(had_errors), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_history(username: str, language: str, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM attempts
        WHERE username = ? AND language = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (username, language, limit)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recent_error_rate(username: str, language: str, last_n: int = 5) -> float:
    history = get_history(username, language, limit=last_n)
    if not history:
        return 0.0
    errors = sum(1 for row in history if row["had_errors"])
    return errors / len(history)