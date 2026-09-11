"""
FastAPI application entry point.

- Lifespan manages the database connection pool lifecycle.
- CORS is configured for local dev and future Vercel deployment.
- Health check endpoint at /api/health.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.api.routes import router as api_router, limiter

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle resources.

    Startup: Initialize the aiosqlite database connection.
    Shutdown: Close the connection gracefully.
    """
    # --- Startup ---
    logger.info("Initializing database...")
    await init_db(settings.database_url)
    logger.info("[SUCCESS] Database initialized")

    yield  # Application runs here

    # --- Shutdown ---
    logger.info("Shutting down database...")
    await close_db()
    logger.info("[SUCCESS] Database connection closed")


app = FastAPI(
    title="Goal-Stack Orchestrator",
    description=(
        "A conversational AI backend that manages multiple concurrent user goals "
        "as a persistent stack — supporting mid-conversation interruption, topic "
        "switching, and resumption without context loss."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# --- Rate Limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
# Allow local Next.js dev server and future Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        # Add your Vercel URL here when deploying:
        # "https://your-app.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# --- Register API routes ---
app.include_router(api_router)


# --- Health Check ---
@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint for Render's monitoring and uptime checks."""
    return {
        "status": "healthy",
        "service": "goal-stack-orchestrator",
        "version": "1.0.0",
    }
