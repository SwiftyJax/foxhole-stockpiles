"""Event type enumeration."""

from enum import Enum


class EventType(str, Enum):
    """Event types for the notification system."""

    # Stockpile scanning events
    STOCKPILE_SCAN_STARTED = "stockpile.scan_started"
    STOCKPILE_SCANNED = "stockpile.scanned"
    STOCKPILE_SCAN_FAILED = "stockpile.scan_failed"

    # Server events
    SERVER_STARTED = "server.started"
    SERVER_STOPPED = "server.stopped"
