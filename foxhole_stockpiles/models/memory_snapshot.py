"""Memory snapshot model."""

from datetime import datetime

from pydantic import BaseModel, Field


class MemorySnapshot(BaseModel):
    """Snapshot of memory usage at a point in time."""

    timestamp: datetime = Field(description="Timestamp of the snapshot")
    rss_mb: float = Field(description="Resident Set Size in MB")
    vms_mb: float = Field(description="Virtual Memory Size in MB")
    percent: float = Field(description="Memory usage percentage")
    available_mb: float = Field(description="Available system memory in MB")
