"""Event system for pub/sub notifications."""

from foxhole_stockpiles.core.events.bus import EventBus, get_event_bus
from foxhole_stockpiles.enums.event_type import EventType

# Backward compatibility
EventTypes = EventType

__all__ = ["EventBus", "EventType", "EventTypes", "get_event_bus"]
