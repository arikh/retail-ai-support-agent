"""
Phase 7: Feedback store.
Captures user feedback per interaction and adapts agent behaviour.
Persists feedback to SQLite for cross-session learning.
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DATABASE_PATH = "data/pricing.db"


class FeedbackStore:
    """
    Stores and retrieves interaction feedback.
    Used to adapt agent behaviour based on past failures.
    """

    def __init__(self):
        self._ensure_table()

    # ── Table setup ───────────────────────────────────────────────────────────

    def _ensure_table(self) -> None:
        """Create feedback table if it doesn't exist."""
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interaction_feedback (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id   TEXT NOT NULL,
                    user_query   TEXT NOT NULL,
                    agent_response TEXT NOT NULL,
                    rating       INTEGER NOT NULL,
                    comment      TEXT,
                    created_at   TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ── Store feedback ────────────────────────────────────────────────────────

    def store(
        self,
        session_id: str,
        user_query: str,
        agent_response: str,
        rating: int,
        comment: str = "",
    ) -> None:
        """
        Store feedback for an interaction.
        rating: 1 = positive, 0 = negative
        """
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            conn.execute(
                """
                INSERT INTO interaction_feedback
                    (session_id, user_query, agent_response, rating, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    user_query,
                    agent_response,
                    rating,
                    comment,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            logger.info(
                f"Feedback stored | Session: {session_id} | "
                f"Rating: {'positive' if rating == 1 else 'negative'}"
            )
        finally:
            conn.close()

    # ── Retrieve feedback ─────────────────────────────────────────────────────

    def get_negative_patterns(self, limit: int = 5) -> list[dict]:
        """
        Return recent negatively-rated queries.
        Used to adapt prompt before responding to similar queries.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT user_query, agent_response, comment, created_at
                FROM interaction_feedback
                WHERE rating = 0
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_summary(self) -> dict:
        """Return overall feedback summary statistics."""
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN rating = 0 THEN 1 ELSE 0 END) as negative
                FROM interaction_feedback
            """)
            row = cursor.fetchone()
            total = row[0] or 0
            positive = row[1] or 0
            negative = row[2] or 0
            return {
                "total": total,
                "positive": positive,
                "negative": negative,
                "score": f"{positive}/{total}" if total > 0 else "0/0",
            }
        finally:
            conn.close()

    # ── Adaptation logic ──────────────────────────────────────────────────────

    def build_adaptation_context(self) -> str:
        """
        Build an adaptation note for the system prompt
        based on recent negative feedback.
        Returns empty string if no negative feedback exists.
        """
        patterns = self.get_negative_patterns(limit=3)
        if not patterns:
            return ""

        note = "\n\nADAPTATION NOTES (based on recent feedback):\n"
        for p in patterns:
            comment = p["comment"] or "no comment provided"
            note += (
                f"- Previous query '{p['user_query'][:60]}' "
                f"received negative feedback: {comment}\n"
            )
        note += (
            "Apply extra care when handling similar queries. "
            "Be more specific, complete, and actionable in your response.\n"
        )
        return note
