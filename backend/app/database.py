"""
Async database connection management for SQLite via aiosqlite.

The database is managed by FastAPI's lifespan - created at startup, closed at shutdown.
We use a single shared connection with WAL mode for concurrent read support.
"""

import asyncio
import logging
import aiosqlite

logger = logging.getLogger(__name__)

# Module-level connection reference, initialized during app startup
_conn: aiosqlite.Connection | None = None
_session_locks: dict[str, asyncio.Lock] = {}


async def init_db(database_url: str) -> aiosqlite.Connection:
    """
    Initialize the SQLite database connection and create tables.

    Args:
        database_url: SQLite database path (e.g., 'orchestrator.db')

    Returns:
        The initialized connection.
    """
    global _conn

    # Strip 'sqlite:///' if present to get the local file path
    db_path = (
        database_url.replace("sqlite:///", "") if database_url else "orchestrator.db"
    )

    logger.info(f"Connecting to SQLite database at {db_path}")
    _conn = await aiosqlite.connect(db_path)

    # SQLite performance & safety pragmas
    await _conn.execute("PRAGMA journal_mode=WAL")
    await _conn.execute("PRAGMA busy_timeout=5000")
    await _conn.execute("PRAGMA foreign_keys=ON")

    # Enable dict factory to access columns by name
    _conn.row_factory = aiosqlite.Row

    # Create tables if they don't exist
    await _conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS goal_stack (
            id TEXT PRIMARY KEY,
            session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
            intent_type TEXT NOT NULL,
            status TEXT NOT NULL,
            slots_filled TEXT DEFAULT '{}',
            slots_missing TEXT DEFAULT '[]',
            stack_position INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            interruptible INTEGER DEFAULT 1,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
            goal_id TEXT REFERENCES goal_stack(id) ON DELETE SET NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            router_decision TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- CRITICAL: Enforce at most one active goal per session at the DB level
        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_goal_per_session
            ON goal_stack (session_id) WHERE status = 'active';

        -- Enforce unique stack positions within a session
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_stack_position
            ON goal_stack (session_id, stack_position);

        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_goals_session_status
            ON goal_stack (session_id, status);

        CREATE INDEX IF NOT EXISTS idx_messages_session_created
            ON messages (session_id, created_at);
    """)
    await _conn.commit()

    return _conn


async def close_db() -> None:
    """Close the database connection gracefully."""
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


def get_db() -> aiosqlite.Connection:
    """
    Get the current database connection.

    Raises:
        RuntimeError: If the DB hasn't been initialized yet.
    """
    if _conn is None:
        raise RuntimeError(
            "Database connection not initialized. "
            "Ensure the app lifespan has started before accessing the database."
        )
    return _conn


def get_session_lock(session_id: str) -> asyncio.Lock:
    """
    Get a per-session write lock. Created lazily on first access.
    Ensures concurrent requests for the SAME session are serialized,
    while requests for DIFFERENT sessions proceed in parallel.
    """
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]
