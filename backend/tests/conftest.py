import os

import pytest_asyncio

from app.database import init_db, close_db

os.environ["GROQ_API_KEY"] = "mock_groq_key_for_testing"
os.environ["GOOGLE_API_KEY"] = "mock_google_key_for_testing"


@pytest_asyncio.fixture(scope="function")
async def db():
    """Provides a fresh, in-memory SQLite database for each test."""
    conn = await init_db(":memory:")
    yield conn
    await close_db()
