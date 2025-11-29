"""FastAPI dependency injection providers."""

from functools import lru_cache

from foxhole_stockpiles.core.events import EventBus, get_event_bus
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.services.notification_service import NotificationService
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator
from foxhole_stockpiles.services.output_coordinator import OutputCoordinator


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


@lru_cache
def get_ocr_coordinator() -> OCRCoordinator:
    """Get the OCR coordinator singleton.

    This creates a single OCRCoordinator instance that is reused across all requests,
    significantly reducing memory usage and initialization overhead.

    Returns:
        OCRCoordinator: The OCR coordinator instance

    Raises:
        ValueError: If database_path is not configured in settings
    """
    settings = get_settings()
    event_bus = get_event_bus()

    if settings.scanner.database_path is None:
        raise ValueError("scanner.database_path must be configured for the server")

    return OCRCoordinator(config=settings.scanner, event_bus=event_bus)


@lru_cache
def get_output_coordinator() -> OutputCoordinator:
    """Get the output coordinator singleton.

    This creates a single OutputCoordinator instance that is reused across all requests,
    reducing memory usage from repeated handler initialization.

    Returns:
        OutputCoordinator: The output coordinator instance
    """
    settings = get_settings()
    return OutputCoordinator(settings=settings)
