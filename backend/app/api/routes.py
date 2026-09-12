"""
API route definitions.

Endpoints:
    POST   /api/sessions           — Create a new conversation session
    GET    /api/sessions/{id}      — Get session details
    POST   /api/sessions/{id}/chat — Send a message (the main endpoint)
    GET    /api/sessions/{id}/goals — Get current goal stack
    GET    /api/sessions/{id}/messages — Get conversation history
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db, get_session_lock
from app.graph.orchestrator import orchestrator_graph
from app.models.message import ChatRequest, ChatResponse, Message
from app.models.session import Session, SessionCreate
from app.services.goal_stack import GoalStackManager
from app.services.session import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"])
limiter = Limiter(key_func=get_remote_address)


# =========================================================================
# Session Endpoints
# =========================================================================


@router.post("/sessions", response_model=Session, status_code=201)
@limiter.limit("20/minute")
async def create_session(request: Request, body: SessionCreate | None = None):
    """Create a new conversation session."""
    db = get_db()
    session_svc = SessionService(db)
    session = await session_svc.create_session(metadata=body.metadata if body else {})
    logger.info(f"Created session: {session.id}")
    return session


@router.get("/sessions/{session_id}", response_model=Session)
@limiter.limit("60/minute")
async def get_session(request: Request, session_id: UUID):
    """Get session details by ID."""
    db = get_db()
    session_svc = SessionService(db)
    session = await session_svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# =========================================================================
# Chat Endpoint — the main endpoint
# =========================================================================


@router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
@limiter.limit("15/minute")
async def chat(request: Request, session_id: UUID, body: ChatRequest):
    """
    Send a message and get a response.

    This is the core endpoint. It:
    1. Passes the message through the LangGraph orchestrator
    2. The orchestrator routes it, executes the right agent, updates the goal stack
    3. Returns the response along with the updated goal stack for the sidebar
    """
    # Verify session exists
    db = get_db()
    session_svc = SessionService(db)
    session = await session_svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Per-session lock: serializes requests for the same session,
        # but allows different sessions to proceed concurrently.
        async with get_session_lock(str(session_id)):
            result = await orchestrator_graph.ainvoke(
                {
                    "session_id": str(session_id),
                    "user_message": body.message,
                    "goal_stack": [],
                    "active_goal": None,
                    "recent_messages": [],
                    "router_decision": None,
                    "agent_response": "",
                    "final_response": {},
                    "messages": [],
                }
            )

        final = result.get("final_response", {})

        return ChatResponse(
            response=final.get("response", "Something went wrong."),
            goal_stack=final.get("goal_stack", []),
            active_goal_id=final.get("active_goal_id"),
            router_decision=final.get("router_decision"),
        )

    except Exception as e:
        logger.error(f"Chat error for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


# =========================================================================
# Goal Stack Endpoint
# =========================================================================


@router.get("/sessions/{session_id}/goals")
@limiter.limit("60/minute")
async def get_goals(request: Request, session_id: UUID):
    """
    Get the current goal stack for a session.

    Used by the frontend sidebar for polling (though normally the
    goal stack is returned with every /chat response).
    """
    db = get_db()
    gsm = GoalStackManager(db)
    stack = await gsm.get_stack(session_id)
    return {
        "session_id": str(stack.session_id),
        "goals": [g.model_dump(mode="json") for g in stack.goals],
        "active_goal": (
            stack.active_goal.model_dump(mode="json") if stack.active_goal else None
        ),
    }


# =========================================================================
# Messages Endpoint
# =========================================================================


@router.get("/sessions/{session_id}/messages", response_model=list[Message])
@limiter.limit("30/minute")
async def get_messages(request: Request, session_id: UUID, limit: int = 50):
    """Get conversation history for a session."""
    db = get_db()
    session_svc = SessionService(db)
    messages = await session_svc.get_messages(session_id, limit=limit)
    return messages
