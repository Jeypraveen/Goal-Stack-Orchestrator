"""
Message-related Pydantic models.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class MessageCreate(BaseModel):
    """Schema for storing a new message."""

    role: Literal["user", "assistant", "system"]
    content: str
    goal_id: UUID | None = None
    router_decision: str | None = None


class Message(BaseModel):
    """A single message in the conversation log."""

    id: int | str
    session_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    goal_id: UUID | None = None
    router_decision: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's message.",
    )


class ChatResponse(BaseModel):
    """Response to a chat request — includes the goal stack for sidebar rendering."""

    response: str = Field(
        ...,
        description="The assistant's natural-language reply.",
    )
    goal_stack: list[dict] = Field(
        default_factory=list,
        description="Current goal stack state for the sidebar.",
    )
    active_goal_id: str | None = Field(
        default=None,
        description="ID of the currently active goal.",
    )
    router_decision: str | None = Field(
        default=None,
        description="What the router classified this message as.",
    )
