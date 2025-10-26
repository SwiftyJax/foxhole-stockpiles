"""Notification service for managing notifiers and event subscriptions."""

import logging
from typing import Any

from foxhole_stockpiles.core.events import EventBus, get_event_bus
from foxhole_stockpiles.core.settings.sections.notifications import NotificationsSettings
from foxhole_stockpiles.enums.notifier_type import NotifierType
from foxhole_stockpiles.notifiers import DiscordNotifier
from foxhole_stockpiles.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages notification handlers and subscribes them to events."""

    def __init__(self, settings: NotificationsSettings, event_bus: EventBus | None = None) -> None:
        """Initialize the notification service.

        Args:
            settings (NotificationsSettings): Notifications configuration
            event_bus (EventBus | None): Optional event bus instance (defaults to global)
        """
        self.settings = settings
        self.event_bus = event_bus or get_event_bus()
        self.notifiers: list[BaseNotifier] = []
        self._initialized = False

    def initialize(self) -> None:
        """Initialize and register all configured notifiers."""
        if self._initialized:
            logger.warning("NotificationService already initialized")
            return

        if not self.settings.enabled:
            logger.info("Notifications are disabled in settings")
            return

        # Setup notifiers from configuration
        for notifier_config in self.settings.notifiers:
            try:
                if notifier_config.type == NotifierType.DISCORD:
                    discord_notifier = DiscordNotifier(
                        webhook_url=notifier_config.webhook_url,
                        username=notifier_config.username,
                        message_templates=notifier_config.message_templates,
                    )
                    # Override the default name with the config name
                    discord_notifier.name = notifier_config.name
                    self._register_notifier(discord_notifier, notifier_config.events)
                    logger.info(f"Discord notifier '{notifier_config.name}' initialized")
                else:
                    logger.warning(f"Unknown notifier type: {notifier_config.type}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize notifier '{notifier_config.name}': {e}", exc_info=True
                )

        self._initialized = True
        logger.info(f"NotificationService initialized with {len(self.notifiers)} notifier(s)")

    def _register_notifier(self, notifier: BaseNotifier, event_types: list[str]) -> None:
        """Register a notifier for specific event types.

        Args:
            notifier (BaseNotifier): The notifier instance
            event_types (list[str]): List of event types this notifier should handle
        """
        self.notifiers.append(notifier)

        # Subscribe the notifier to each event type
        for event_type in event_types:
            handler = self._create_handler(notifier, event_type)
            self.event_bus.subscribe(event_type, handler)
            logger.debug(f"Registered {notifier.name} for event '{event_type}'")

    def _create_handler(self, notifier: BaseNotifier, event_type: str) -> Any:
        """Create an event handler for a notifier.

        Args:
            notifier (BaseNotifier): The notifier instance
            event_type (str): The event type this handler will handle

        Returns:
            Any: Callable handler function
        """

        def handler(data: dict[str, Any]) -> None:
            """Handle event by sending notification."""
            try:
                # Note: We can't use await here since event handlers are sync
                # We'll need to handle this differently in production
                import asyncio

                # Try to get the running loop, or create one
                try:
                    loop = asyncio.get_running_loop()
                    # Schedule the coroutine
                    loop.create_task(notifier.send(event_type, data))
                except RuntimeError:
                    # No running loop, run it synchronously
                    asyncio.run(notifier.send(event_type, data))
            except Exception as e:
                logger.error(f"Failed to send notification via {notifier.name}: {e}")

        return handler

    def shutdown(self) -> None:
        """Shutdown the notification service and cleanup resources."""
        logger.info("Shutting down NotificationService")
        self.notifiers.clear()
        self._initialized = False
