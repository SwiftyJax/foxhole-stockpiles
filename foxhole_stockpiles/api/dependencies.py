"""FastAPI dependency injection providers."""

from functools import lru_cache

from foxhole_stockpiles.core.events import EventBus, get_event_bus
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.services.notification_service import NotificationService


@lru_cache
def get_notification_service() -> NotificationService:
    """Get the notification service singleton.

    Returns:
        NotificationService: The notification service instance
    """
    settings = get_settings()
    event_bus = get_event_bus()
    service = NotificationService(settings.notifications, event_bus=event_bus)
    service.initialize()
    return service


def get_event_bus_dependency() -> EventBus:
    """Get the event bus for dependency injection.

    Returns:
        EventBus: The global event bus instance
    """
    return get_event_bus()
