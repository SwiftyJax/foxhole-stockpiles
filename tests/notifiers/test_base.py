"""Tests for notifiers.base module."""

from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.notifiers.base import BaseNotifier


class ConcreteNotifier(BaseNotifier):
    """Concrete implementation of BaseNotifier for testing."""

    def __init__(self, name: str = "Test") -> None:
        """Initialize test notifier."""
        super().__init__(name)
        self.send_called = False
        self.last_event_type: str | None = None
        self.last_data: dict[str, Any] | None = None

    async def send(self, event_type: str, data: dict[str, Any]) -> None:
        """Record send calls for testing."""
        self.send_called = True
        self.last_event_type = event_type
        self.last_data = data


class TestBaseNotifierInitialization:
    """Test suite for BaseNotifier initialization."""

    def test_init_sets_name_and_enabled(self) -> None:
        """Test that initialization sets name and enabled flag."""
        notifier = ConcreteNotifier(name="TestNotifier")

        assert notifier.name == "TestNotifier"
        assert notifier.enabled is True


class TestFormatMessage:
    """Test suite for BaseNotifier.format_message method."""

    def test_format_message_basic(self) -> None:
        """Test formatting a simple message."""
        notifier = ConcreteNotifier()
        data = {"key1": "value1", "key2": "value2"}

        message = notifier.format_message("test_event", data)

        assert "Event: test_event" in message
        assert "key1: value1" in message
        assert "key2: value2" in message
        assert " | " in message

    def test_format_message_excludes_timestamp(self) -> None:
        """Test that timestamp is excluded from formatted message."""
        notifier = ConcreteNotifier()
        data = {"key1": "value1", "timestamp": "2024-01-01"}

        message = notifier.format_message("test_event", data)

        assert "Event: test_event" in message
        assert "key1: value1" in message
        assert "timestamp" not in message

    def test_format_message_empty_data(self) -> None:
        """Test formatting message with empty data."""
        notifier = ConcreteNotifier()
        data: dict[str, Any] = {}

        message = notifier.format_message("test_event", data)

        assert message == "Event: test_event"

    def test_format_message_with_various_types(self) -> None:
        """Test formatting message with different value types."""
        notifier = ConcreteNotifier()
        data = {
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
        }

        message = notifier.format_message("test_event", data)

        assert "string: text" in message
        assert "int: 42" in message
        assert "float: 3.14" in message
        assert "bool: True" in message
        assert "none: None" in message


class TestEnableDisable:
    """Test suite for BaseNotifier enable/disable methods."""

    def test_enable_sets_flag_and_logs(self) -> None:
        """Test that enable() sets the enabled flag and logs."""
        notifier = ConcreteNotifier(name="TestNotifier")
        notifier.enabled = False

        with patch("foxhole_stockpiles.notifiers.base.logger") as mock_logger:
            notifier.enable()

            assert notifier.enabled is True
            mock_logger.info.assert_called_once_with("Notifier 'TestNotifier' enabled")

    def test_disable_sets_flag_and_logs(self) -> None:
        """Test that disable() sets the enabled flag and logs."""
        notifier = ConcreteNotifier(name="TestNotifier")
        notifier.enabled = True

        with patch("foxhole_stockpiles.notifiers.base.logger") as mock_logger:
            notifier.disable()

            assert notifier.enabled is False
            mock_logger.info.assert_called_once_with("Notifier 'TestNotifier' disabled")

    def test_enable_when_already_enabled(self) -> None:
        """Test enabling when already enabled."""
        notifier = ConcreteNotifier()
        notifier.enabled = True

        with patch("foxhole_stockpiles.notifiers.base.logger") as mock_logger:
            notifier.enable()

            assert notifier.enabled is True
            mock_logger.info.assert_called_once()

    def test_disable_when_already_disabled(self) -> None:
        """Test disabling when already disabled."""
        notifier = ConcreteNotifier()
        notifier.enabled = False

        with patch("foxhole_stockpiles.notifiers.base.logger") as mock_logger:
            notifier.disable()

            assert notifier.enabled is False
            mock_logger.info.assert_called_once()


class TestAbstractMethods:
    """Test suite for abstract method enforcement."""

    def test_send_must_be_implemented(self) -> None:
        """Test that send() must be implemented by subclasses."""

        class IncompleteNotifier(BaseNotifier):
            """Notifier that doesn't implement send()."""

            pass

        # Should not be able to instantiate without implementing send()
        with pytest.raises(TypeError):
            IncompleteNotifier("test")  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_base_send_raises_not_implemented(self) -> None:
        """Test that calling base send() raises NotImplementedError."""

        class NotifierThatCallsSuper(BaseNotifier):
            """Notifier that calls super().send()."""

            async def send(self, event_type: str, data: dict[str, Any]) -> None:
                """Call parent send to trigger NotImplementedError."""
                await super().send(event_type, data)  # type: ignore[safe-super]

        notifier = NotifierThatCallsSuper("test")

        with pytest.raises(NotImplementedError):
            await notifier.send("test_event", {})
