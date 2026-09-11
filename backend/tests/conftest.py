import pytest_asyncio

from app.database import init_db, close_db


@pytest_asyncio.fixture(scope="function")
async def db():
    """Provides a fresh, in-memory SQLite database for each test."""
    conn = await init_db(":memory:")
    yield conn
    await close_db()
