"""Base notifier class."""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """Abstract base class for notification handlers."""

    def __init__(self, name: str) -> None:
        """Initialize the notifier.

        Args:
            name (str): Human-readable name for this notifier
        """
        self.name = name
        self.enabled = True

    @abstractmethod
    async def send(self, event_type: str, data: dict[str, Any]) -> None:
        """Send a notification.

        Args:
            event_type (str): The type of event that triggered this notification
            data (dict[str, Any]): Event data to include in the notification

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def format_message(self, event_type: str, data: dict[str, Any]) -> str:
        """Format event data into a human-readable message.

        Default implementation provides a simple format.
        Subclasses can override for custom formatting.

        Args:
            event_type (str): The type of event
            data (dict[str, Any]): Event data

        Returns:
            str: Formatted message
        """
        # Default formatting
        parts = [f"Event: {event_type}"]
        for key, value in data.items():
            if key != "timestamp":
                parts.append(f"{key}: {value}")
        return " | ".join(parts)

    def enable(self) -> None:
        """Enable this notifier."""
        self.enabled = True
        logger.info(f"Notifier '{self.name}' enabled")

    def disable(self) -> None:
        """Disable this notifier."""
        self.enabled = False
        logger.info(f"Notifier '{self.name}' disabled")
