"""Request memory statistics model."""

from datetime import datetime

from pydantic import BaseModel, Field


class RequestMemoryStats(BaseModel):
    """Memory statistics for a single request."""

    path: str = Field(description="Request path")
    method: str = Field(description="HTTP method")
    timestamp: datetime = Field(description="Request timestamp")
    duration_ms: float = Field(description="Request duration in milliseconds")
    memory_before_mb: float = Field(description="Memory before request in MB")
    memory_after_mb: float = Field(description="Memory after request in MB")
    memory_delta_mb: float = Field(description="Memory change in MB")
    status_code: int = Field(description="HTTP response status code")
