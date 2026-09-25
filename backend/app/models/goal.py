"""
Goal-related Pydantic models.

These models define the shape of goals on the stack - the central data structure
of the entire orchestrator. Used for API serialization, database read/write,
and the frontend sidebar rendering.
"""

from datetime import datetime
from typing import Literal, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class Goal(BaseModel):
    """
    A single goal on the stack.

    This is the core domain object. Each goal tracks:
    - What the user wants (intent_type)
    - What info has been collected (slots_filled)
    - What info is still needed (slots_missing)
    - Where it sits on the stack (stack_position)
    - Its lifecycle state (status)
    """

    id: UUID
    session_id: UUID
    intent_type: Literal["booking", "faq", "status"]
    status: Literal["active", "paused", "completed", "abandoned"]
    slots_filled: dict
    slots_missing: list[str]
    stack_position: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    interruptible: bool = True

    model_config = ConfigDict(from_attributes=True)


class AgentResponse(BaseModel):
    """
    Standardized response from any agent back to the orchestrator.
    """

    response: str
    slots_filled: dict[str, Any] = Field(default_factory=dict)
    slots_missing: list[str] = Field(default_factory=list)
    is_complete: bool = False

    model_config = ConfigDict(from_attributes=True)


class GoalStackState(BaseModel):
    """
    The full goal stack for a session.

    Returned to the frontend for sidebar rendering. Goals are ordered
    by stack_position descending (top of stack first).
    """

    session_id: UUID
    goals: list[Goal] = Field(
        default_factory=list,
        description="All goals in the session, ordered by stack_position descending.",
    )
    active_goal: Goal | None = Field(
        default=None,
        description="The currently active goal (top of stack with status='active').",
    )
