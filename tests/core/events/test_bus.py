"""Tests for core.events.bus module.

This module contains comprehensive tests for the EventBus class,
which handles pub/sub event management for the notification system.
"""

from unittest.mock import MagicMock, patch

from foxhole_stockpiles.core.events.bus import EventBus
from foxhole_stockpiles.enums.event_type import EventType


class TestEventBusInitialization:
    """Test suite for EventBus initialization.

    This class contains tests for proper initialization of the EventBus
    including subscribers dictionary and initial state validation.
    """

    def test_init_creates_empty_subscribers(self) -> None:
        """Test that initialization creates empty subscribers dictionary."""
        bus = EventBus()
        assert len(bus._subscribers) == 0


class TestSubscribe:
    """Test suite for EventBus.subscribe method.

    This class contains tests for subscribing handlers to events.
    """

    def test_subscribe_single_handler(self) -> None:
        """Test subscribing a single handler to an event."""
        bus = EventBus()
        handler = MagicMock(__name__="test_handler")

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler)

        assert EventType.STOCKPILE_SCANNED in bus._subscribers
        assert handler in bus._subscribers[EventType.STOCKPILE_SCANNED]

    def test_subscribe_multiple_handlers_to_same_event(self) -> None:
        """Test subscribing multiple handlers to the same event."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1")
        handler2 = MagicMock(__name__="handler2")

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler1)
        bus.subscribe(EventType.STOCKPILE_SCANNED, handler2)

        assert len(bus._subscribers[EventType.STOCKPILE_SCANNED]) == 2
        assert handler1 in bus._subscribers[EventType.STOCKPILE_SCANNED]
        assert handler2 in bus._subscribers[EventType.STOCKPILE_SCANNED]

    def test_subscribe_handler_to_multiple_events(self) -> None:
        """Test subscribing the same handler to multiple events."""
        bus = EventBus()
        handler = MagicMock(__name__="multi_handler")

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler)
        bus.subscribe(EventType.STOCKPILE_SCAN_FAILED, handler)

        assert handler in bus._subscribers[EventType.STOCKPILE_SCANNED]
        assert handler in bus._subscribers[EventType.STOCKPILE_SCAN_FAILED]


class TestUnsubscribe:
    """Test suite for EventBus.unsubscribe method.

    This class contains tests for unsubscribing handlers from events.
    """

    def test_unsubscribe_existing_handler(self) -> None:
        """Test unsubscribing an existing handler."""
        bus = EventBus()
        handler = MagicMock(__name__="test_handler")

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler)
        bus.unsubscribe(EventType.STOCKPILE_SCANNED, handler)

        assert handler not in bus._subscribers[EventType.STOCKPILE_SCANNED]

    def test_unsubscribe_nonexistent_handler(self) -> None:
        """Test unsubscribing a handler that doesn't exist (should not raise)."""
        bus = EventBus()
        handler = MagicMock(__name__="nonexistent_handler")

        # Should not raise an exception
        bus.unsubscribe(EventType.STOCKPILE_SCANNED, handler)

    def test_unsubscribe_handler_not_subscribed_logs_warning(self) -> None:
        """Test that unsubscribing a non-subscribed handler logs a warning."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1")
        handler2 = MagicMock(__name__="handler2")

        # Subscribe handler1, then try to unsubscribe handler2
        bus.subscribe(EventType.STOCKPILE_SCANNED, handler1)

        with patch("foxhole_stockpiles.core.events.bus.logger") as mock_logger:
            bus.unsubscribe(EventType.STOCKPILE_SCANNED, handler2)
            mock_logger.warning.assert_called_once()

    def test_unsubscribe_one_of_multiple_handlers(self) -> None:
        """Test unsubscribing one handler when multiple are subscribed."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1")
        handler2 = MagicMock(__name__="handler2")

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler1)
        bus.subscribe(EventType.STOCKPILE_SCANNED, handler2)
        bus.unsubscribe(EventType.STOCKPILE_SCANNED, handler1)

        assert handler1 not in bus._subscribers[EventType.STOCKPILE_SCANNED]
        assert handler2 in bus._subscribers[EventType.STOCKPILE_SCANNED]


class TestEmit:
    """Test suite for EventBus.emit method.

    This class contains tests for emitting events to subscribed handlers.
    """

    def test_emit_calls_subscribed_handler(self) -> None:
        """Test that emitting an event calls the subscribed handler."""
        bus = EventBus()
        handler = MagicMock(__name__="test_handler")
        test_data = {"key": "value"}

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler)
        bus.emit(EventType.STOCKPILE_SCANNED, test_data)

        handler.assert_called_once_with(test_data)

    def test_emit_calls_all_subscribed_handlers(self) -> None:
        """Test that emitting an event calls all subscribed handlers."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1")
        handler2 = MagicMock(__name__="handler2")
        test_data = {"key": "value"}

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler1)
        bus.subscribe(EventType.STOCKPILE_SCANNED, handler2)
        bus.emit(EventType.STOCKPILE_SCANNED, test_data)

        handler1.assert_called_once_with(test_data)
        handler2.assert_called_once_with(test_data)

    def test_emit_with_no_subscribers(self) -> None:
        """Test that emitting an event with no subscribers doesn't raise."""
        bus = EventBus()
        test_data = {"key": "value"}

        # Should not raise an exception
        bus.emit(EventType.STOCKPILE_SCANNED, test_data)

    def test_emit_continues_after_handler_exception(self) -> None:
        """Test that emit continues calling handlers even if one raises an exception."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1", side_effect=Exception("Handler 1 failed"))
        handler2 = MagicMock(__name__="handler2")
        test_data = {"key": "value"}

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler1)
        bus.subscribe(EventType.STOCKPILE_SCANNED, handler2)
        bus.emit(EventType.STOCKPILE_SCANNED, test_data)

        # Both handlers should have been called
        handler1.assert_called_once_with(test_data)
        handler2.assert_called_once_with(test_data)

    def test_emit_only_calls_handlers_for_specific_event(self) -> None:
        """Test that emit only calls handlers subscribed to the specific event."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1")
        handler2 = MagicMock(__name__="handler2")
        test_data = {"key": "value"}

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler1)
        bus.subscribe(EventType.STOCKPILE_SCAN_FAILED, handler2)
        bus.emit(EventType.STOCKPILE_SCANNED, test_data)

        handler1.assert_called_once_with(test_data)
        handler2.assert_not_called()


class TestClear:
    """Test suite for EventBus.clear method.

    This class contains tests for clearing all subscriptions.
    """

    def test_clear_removes_all_subscriptions(self) -> None:
        """Test that clear removes all subscriptions."""
        bus = EventBus()
        handler1 = MagicMock(__name__="handler1")
        handler2 = MagicMock(__name__="handler2")

        bus.subscribe(EventType.STOCKPILE_SCANNED, handler1)
        bus.subscribe(EventType.STOCKPILE_SCAN_FAILED, handler2)

        bus.clear()

        assert len(bus._subscribers) == 0

    def test_clear_logs_debug_message(self) -> None:
        """Test that clear logs a debug message."""
        bus = EventBus()
        handler = MagicMock(__name__="handler")
        bus.subscribe(EventType.STOCKPILE_SCANNED, handler)

        with patch("foxhole_stockpiles.core.events.bus.logger") as mock_logger:
            bus.clear()
            mock_logger.debug.assert_called()

    def test_clear_on_empty_bus(self) -> None:
        """Test that clear works on an empty bus."""
        bus = EventBus()

        # Should not raise
        bus.clear()

        assert len(bus._subscribers) == 0
