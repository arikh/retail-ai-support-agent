"""
Phase 6: Session memory manager.
Maintains conversation history within a session.
Supports short-term memory (current session) and
long-term memory (persisted across sessions via SQLite).
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)

DATABASE_PATH = "data/pricing.db"


class SessionMemory:
    """
    Manages conversation history for a single session.

    Short-term memory: in-memory list of messages for current session.
    Long-term memory: key facts persisted to SQLite across sessions.
    """

    def __init__(self, session_id: str, max_history: int = 10):
        self.session_id   = session_id
        self.max_history  = max_history
        self.messages: list[BaseMessage] = []
        self._ensure_tables()
        self._load_long_term_memory()

    # ── Table setup ───────────────────────────────────────────────────────────

    def _ensure_tables(self) -> None:
        """Create memory tables if they don't exist."""
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_memory (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT NOT NULL,
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    created_at  TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT NOT NULL,
                    key         TEXT NOT NULL,
                    value       TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    UNIQUE(session_id, key)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ── Short-term memory ─────────────────────────────────────────────────────

    def add_user_message(self, content: str) -> None:
        """Add a user message to history."""
        self.messages.append(HumanMessage(content=content))
        self._trim_history()
        logger.info(f"Memory | Session: {self.session_id} | User: {content[:50]}")

    def add_ai_message(self, content: str) -> None:
        """Add an AI message to history."""
        self.messages.append(AIMessage(content=content))
        self._trim_history()

    def get_history(self) -> list[BaseMessage]:
        """Return current conversation history."""
        return self.messages.copy()

    def _trim_history(self) -> None:
        """Keep only the last N message pairs to avoid context overflow."""
        if len(self.messages) > self.max_history * 2:
            self.messages = self.messages[-(self.max_history * 2):]
            logger.info(f"Memory trimmed to {self.max_history} pairs")

    def clear_session(self) -> None:
        """Clear current session memory."""
        self.messages = []
        logger.info(f"Session memory cleared: {self.session_id}")

    # ── Long-term memory ──────────────────────────────────────────────────────

    def remember(self, key: str, value: str) -> None:
        """
        Store a key fact in long-term memory.
        Persists across sessions.
        Example: remember('last_plan', 'SUMMER_LATAM_V2')
        """
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            conn.execute("""
                INSERT INTO long_term_memory
                    (session_id, key, value, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, key)
                DO UPDATE SET value=excluded.value, created_at=excluded.created_at
            """, (self.session_id, key, value, datetime.now().isoformat()))
            conn.commit()
            logger.info(f"Long-term memory stored: {key}={value}")
        finally:
            conn.close()

    def recall(self, key: str) -> str | None:
        """Retrieve a fact from long-term memory."""
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.execute("""
                SELECT value FROM long_term_memory
                WHERE session_id = ? AND key = ?
            """, (self.session_id, key))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def _load_long_term_memory(self) -> None:
        """Load long-term memory summary into context at session start."""
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.execute("""
                SELECT key, value FROM long_term_memory
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (self.session_id,))
            rows = cursor.fetchall()
            if rows:
                context = "Previously remembered context:\n"
                context += "\n".join([f"- {k}: {v}" for k, v in rows])
                self.messages.append(AIMessage(content=context))
                logger.info(
                    f"Loaded {len(rows)} long-term memory items "
                    f"for session {self.session_id}"
                )
        finally:
            conn.close()

    def get_memory_summary(self) -> dict:
        """Return summary of current memory state."""
        return {
            "session_id":     self.session_id,
            "message_count":  len(self.messages),
            "max_history":    self.max_history,
        }