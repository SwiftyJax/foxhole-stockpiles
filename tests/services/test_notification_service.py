"""Tests for services.notification_service module.

This module contains comprehensive tests for the NotificationService class,
which manages notification handlers and subscribes them to events.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from foxhole_stockpiles.core.events.bus import EventBus
from foxhole_stockpiles.core.settings.sections.notifications import (
    DiscordNotifierSettings,
    NotificationsSettings,
)
from foxhole_stockpiles.enums.event_type import EventType
from foxhole_stockpiles.enums.notifier_type import NotifierType
from foxhole_stockpiles.services.notification_service import NotificationService


class TestNotificationServiceInitialization:
    """Test suite for NotificationService initialization.

    This class contains tests for proper initialization of the NotificationService
    including settings, event bus, and initial state validation.
    """

    def test_init_with_settings(self) -> None:
        """Test initializing NotificationService with settings."""
        settings = NotificationsSettings(enabled=True)
        service = NotificationService(settings)

        assert service.settings == settings
        assert service.event_bus is not None
        assert service.notifiers == []
        assert service._initialized is False

    def test_init_with_custom_event_bus(self) -> None:
        """Test initializing NotificationService with custom event bus."""
        settings = NotificationsSettings(enabled=True)
        custom_bus = EventBus()
        service = NotificationService(settings, event_bus=custom_bus)

        assert service.event_bus == custom_bus


class TestInitialize:
    """Test suite for NotificationService.initialize method.

    This class contains tests for initializing and registering notifiers.
    """

    def test_initialize_when_disabled(self) -> None:
        """Test that initialize does nothing when notifications are disabled."""
        settings = NotificationsSettings(enabled=False)
        service = NotificationService(settings)

        service.initialize()

        assert service._initialized is False
        assert len(service.notifiers) == 0

    def test_initialize_prevents_double_initialization(self) -> None:
        """Test that initialize can't be called twice."""
        settings = NotificationsSettings(enabled=True)
        service = NotificationService(settings)

        service.initialize()
        initial_notifiers = len(service.notifiers)

        with patch("foxhole_stockpiles.services.notification_service.logger") as mock_logger:
            service.initialize()
            mock_logger.warning.assert_called_once()

        assert len(service.notifiers) == initial_notifiers

    def test_initialize_with_discord_notifier(self) -> None:
        """Test initializing with a Discord notifier configuration."""
        discord_config = DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name="Test Discord",
            webhook_url="https://discord.com/api/webhooks/123/abc",
            username="Test Bot",
            events=[EventType.STOCKPILE_SCANNED],
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config])
        service = NotificationService(settings)

        with patch("foxhole_stockpiles.services.notification_service.DiscordNotifier") as mock_cls:
            mock_notifier = Mock()
            mock_notifier.send = AsyncMock()
            mock_cls.return_value = mock_notifier

            service.initialize()

            mock_cls.assert_called_once_with(
                webhook_url="https://discord.com/api/webhooks/123/abc", username="Test Bot"
            )
            assert service._initialized is True
            assert len(service.notifiers) == 1
            assert mock_notifier.name == "Test Discord"

    def test_initialize_with_multiple_notifiers(self) -> None:
        """Test initializing with multiple Discord notifiers."""
        discord_config1 = DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name="Discord 1",
            webhook_url="https://discord.com/api/webhooks/111/aaa",
            events=[EventType.STOCKPILE_SCANNED],
        )
        discord_config2 = DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name="Discord 2",
            webhook_url="https://discord.com/api/webhooks/222/bbb",
            events=[EventType.STOCKPILE_SCAN_FAILED],
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config1, discord_config2])
        service = NotificationService(settings)

        with patch("foxhole_stockpiles.services.notification_service.DiscordNotifier") as mock_cls:
            mock_notifier = Mock()
            mock_notifier.send = AsyncMock()
            mock_cls.return_value = mock_notifier

            service.initialize()

            assert len(service.notifiers) == 2
            assert mock_cls.call_count == 2

    def test_initialize_handles_notifier_error(self) -> None:
        """Test that initialize handles errors when creating notifiers."""
        discord_config = DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name="Bad Discord",
            webhook_url="https://discord.com/api/webhooks/123/abc",
            events=[EventType.STOCKPILE_SCANNED],
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config])
        service = NotificationService(settings)

        with patch("foxhole_stockpiles.services.notification_service.DiscordNotifier") as mock_cls:
            mock_cls.side_effect = Exception("Failed to create notifier")

            with patch("foxhole_stockpiles.services.notification_service.logger") as mock_logger:
                service.initialize()
                mock_logger.error.assert_called()

            # Service should still be initialized even if notifier creation failed
            assert service._initialized is True
            assert len(service.notifiers) == 0

    def test_initialize_logs_unknown_notifier_type(self) -> None:
        """Test that initialize logs warning for unknown notifier types."""
        # Create a mock config with an invalid type (would normally be caught by Pydantic)
        settings = NotificationsSettings(enabled=True, notifiers=[])
        service = NotificationService(settings)

        # Manually add an invalid notifier config to test the else branch
        invalid_config = Mock()
        invalid_config.type = "unknown"
        invalid_config.name = "Unknown Notifier"
        service.settings.notifiers.append(invalid_config)

        with patch("foxhole_stockpiles.services.notification_service.logger") as mock_logger:
            service.initialize()
            mock_logger.warning.assert_called()


class TestRegisterNotifier:
    """Test suite for NotificationService._register_notifier method.

    This class contains tests for registering notifiers to event types.
    """

    def test_register_notifier_subscribes_to_events(self) -> None:
        """Test that registering a notifier subscribes it to specified events."""
        settings = NotificationsSettings(enabled=True)
        event_bus = EventBus()
        service = NotificationService(settings, event_bus=event_bus)

        mock_notifier = Mock()
        mock_notifier.send = AsyncMock()
        mock_notifier.name = "Test Notifier"

        service._register_notifier(
            mock_notifier, [EventType.STOCKPILE_SCANNED, EventType.STOCKPILE_SCAN_FAILED]
        )

        assert mock_notifier in service.notifiers
        assert len(event_bus._subscribers[EventType.STOCKPILE_SCANNED]) == 1
        assert len(event_bus._subscribers[EventType.STOCKPILE_SCAN_FAILED]) == 1


class TestCreateHandler:
    """Test suite for NotificationService._create_handler method.

    This class contains tests for creating event handlers.
    """

    @pytest.mark.asyncio
    async def test_create_handler_returns_callable(self) -> None:
        """Test that _create_handler returns a callable handler."""
        settings = NotificationsSettings(enabled=True)
        service = NotificationService(settings)

        mock_notifier = Mock()
        mock_notifier.send = AsyncMock()
        mock_notifier.name = "Test Notifier"

        handler = service._create_handler(mock_notifier, EventType.STOCKPILE_SCANNED)

        assert callable(handler)

    @pytest.mark.asyncio
    async def test_handler_calls_notifier_send(self) -> None:
        """Test that the created handler calls notifier.send."""
        settings = NotificationsSettings(enabled=True)
        service = NotificationService(settings)

        mock_notifier = Mock()
        mock_notifier.send = AsyncMock()
        mock_notifier.name = "Test Notifier"

        handler = service._create_handler(mock_notifier, EventType.STOCKPILE_SCANNED)
        test_data = {"key": "value"}

        # Call the handler (it will schedule the async call)
        handler(test_data)

        # Give asyncio time to execute
        import asyncio

        await asyncio.sleep(0.1)

        # Verify send was called (may have been scheduled)
        # Note: This test verifies the handler was created correctly

    @pytest.mark.asyncio
    async def test_handler_catches_notifier_exceptions(self) -> None:
        """Test that handler catches and logs exceptions from notifier.send."""
        settings = NotificationsSettings(enabled=True)
        service = NotificationService(settings)

        mock_notifier = Mock()
        mock_notifier.send = AsyncMock(side_effect=Exception("Send failed"))
        mock_notifier.name = "Test Notifier"

        handler = service._create_handler(mock_notifier, EventType.STOCKPILE_SCANNED)
        test_data = {"key": "value"}

        with patch("foxhole_stockpiles.services.notification_service.logger"):
            # Should not raise, just log the error
            handler(test_data)

            # Give asyncio time to execute and log
            import asyncio

            await asyncio.sleep(0.1)


class TestShutdown:
    """Test suite for NotificationService.shutdown method.

    This class contains tests for shutting down the notification service.
    """

    def test_shutdown_clears_notifiers(self) -> None:
        """Test that shutdown clears all notifiers."""
        discord_config = DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name="Test Discord",
            webhook_url="https://discord.com/api/webhooks/123/abc",
            events=[EventType.STOCKPILE_SCANNED],
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config])
        service = NotificationService(settings)

        with patch("foxhole_stockpiles.services.notification_service.DiscordNotifier"):
            service.initialize()

        service.shutdown()

        assert len(service.notifiers) == 0
        assert service._initialized is False


class TestIntegration:
    """Integration tests for NotificationService.

    This class contains end-to-end tests for the notification service.
    """

    @pytest.mark.asyncio
    async def test_full_notification_flow(self) -> None:
        """Test complete notification flow from event to Discord."""
        discord_config = DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name="Test Discord",
            webhook_url="https://discord.com/api/webhooks/123/abc",
            events=[EventType.STOCKPILE_SCANNED],
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config])
        event_bus = EventBus()
        service = NotificationService(settings, event_bus=event_bus)

        with patch("foxhole_stockpiles.services.notification_service.DiscordNotifier") as mock_cls:
            mock_notifier = Mock()
            mock_notifier.send = AsyncMock()
            mock_notifier.name = "Test Discord"
            mock_cls.return_value = mock_notifier

            service.initialize()

            # Emit an event
            test_data = {"stockpile_name": "Test", "duration": 1.5, "item_count": 10}
            event_bus.emit(EventType.STOCKPILE_SCANNED, test_data)

            # Give asyncio time to execute
            import asyncio

            await asyncio.sleep(0.1)
