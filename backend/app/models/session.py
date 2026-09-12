"""
Session-related Pydantic models.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class SessionCreate(BaseModel):
    """Schema for creating a new conversation session."""

    metadata: dict = Field(
        default_factory=dict,
        description="Optional metadata to attach to the session.",
    )

    @field_validator("metadata")
    @classmethod
    def validate_metadata_size(cls, v: dict) -> dict:
        import json

        if len(json.dumps(v)) > 1024:
            raise ValueError("Metadata too large (max 1024 bytes)")
        return v


class Session(BaseModel):
    """A conversation session."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    metadata: dict

    model_config = ConfigDict(from_attributes=True)
