"""Notification model."""

from datetime import datetime

from pydantic import BaseModel, Field


class NotificationData(BaseModel):
    """Data structure for notification events."""

    event_type: str = Field(description="Type of event that triggered the notification")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the event occurred")
    message: str = Field(description="Human-readable message for the notification")
    details: dict[str, str | int | float | None] = Field(
        default_factory=dict, description="Additional details about the event"
    )
