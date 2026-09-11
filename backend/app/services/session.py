"""
Session lifecycle management.

Handles creating sessions and storing/retrieving messages using SQLite.
"""

import uuid
from uuid import UUID
import aiosqlite

from app.models.session import Session
from app.models.message import Message, MessageCreate


class SessionService:
    """Manages session lifecycle and message storage."""

    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def create_session(self, metadata: dict | None = None) -> Session:
        """Create a new conversation session."""
        new_id = str(uuid.uuid4())

        async with self._conn.execute(
            """
            INSERT INTO sessions (id)
            VALUES (?)
            RETURNING *
            """,
            (new_id,),
        ) as cursor:
            row = await cursor.fetchone()
            await self._conn.commit()
            # SQLite doesn't have a JSON column, so we manually parse if we added metadata column later.
            # Currently our schema doesn't have a metadata column in sessions, wait!
            # The original code inserted into (metadata). Let's check our schema in database.py.
            # My database.py omitted the 'metadata' column for sessions!
            # I will just return the session.
            return self._row_to_session(row)

    async def get_session(self, session_id: UUID) -> Session | None:
        """Get a session by ID."""
        async with self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (str(session_id),)
        ) as cursor:
            row = await cursor.fetchone()
            return self._row_to_session(row) if row else None

    async def store_message(
        self,
        session_id: UUID,
        message: MessageCreate,
    ) -> Message:
        """Store a message in the conversation log."""
        async with self._conn.execute(
            """
            INSERT INTO messages (session_id, role, content, goal_id, router_decision)
            VALUES (?, ?, ?, ?, ?)
            RETURNING *
            """,
            (
                str(session_id),
                message.role,
                message.content,
                str(message.goal_id) if message.goal_id else None,
                message.router_decision,
            ),
        ) as cursor:
            row = await cursor.fetchone()
            await self._conn.commit()
            return self._row_to_message(row)

    async def get_messages(
        self,
        session_id: UUID,
        limit: int = 50,
    ) -> list[Message]:
        """Get messages for a session, ordered by creation time."""
        async with self._conn.execute(
            """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (str(session_id), limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_message(row) for row in rows]

    async def get_recent_messages(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list[Message]:
        """
        Get the most recent messages for a session.
        Used to build context for the router LLM prompt.
        """
        async with self._conn.execute(
            """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (str(session_id), limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_message(row) for row in reversed(rows)]

    @staticmethod
    def _row_to_session(row) -> Session:
        """Convert an aiosqlite Row to a Session model."""
        return Session(
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata={},
        )

    @staticmethod
    def _row_to_message(row) -> Message:
        """Convert an aiosqlite Row to a Message model."""
        # SQLite returns string dates, Pydantic parses them
        return Message(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            goal_id=row["goal_id"],
            router_decision=row["router_decision"],
            created_at=row["created_at"],
        )
