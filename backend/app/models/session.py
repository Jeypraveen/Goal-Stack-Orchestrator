"""
Session-related Pydantic models.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SessionCreate(BaseModel):
    """Schema for creating a new conversation session."""

    metadata: dict = Field(
        default_factory=dict,
        description="Optional metadata to attach to the session.",
    )


class Session(BaseModel):
    """A conversation session."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    metadata: dict

    model_config = ConfigDict(from_attributes=True)
