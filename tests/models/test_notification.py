"""Tests for models.notification module."""

from datetime import datetime

from foxhole_stockpiles.models.notification import NotificationData


class TestNotificationData:
    """Test suite for NotificationData model."""

    def test_create_notification_data_with_all_fields(self) -> None:
        """Test creating NotificationData with all fields specified."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        details: dict[str, str | int | float | None] = {"key": "value", "count": 42, "ratio": 3.14}

        notification = NotificationData(
            event_type="test_event",
            timestamp=timestamp,
            message="Test message",
            details=details,
        )

        assert notification.event_type == "test_event"
        assert notification.timestamp == timestamp
        assert notification.message == "Test message"
        assert notification.details == details

    def test_create_notification_data_with_minimal_fields(self) -> None:
        """Test creating NotificationData with only required fields."""
        notification = NotificationData(
            event_type="minimal_event",
            message="Minimal message",
        )

        assert notification.event_type == "minimal_event"
        assert notification.message == "Minimal message"
        assert isinstance(notification.timestamp, datetime)
        assert notification.details == {}

    def test_timestamp_defaults_to_current_time(self) -> None:
        """Test that timestamp defaults to current time."""
        before = datetime.now()
        notification = NotificationData(
            event_type="test",
            message="test",
        )
        after = datetime.now()

        assert before <= notification.timestamp <= after

    def test_details_defaults_to_empty_dict(self) -> None:
        """Test that details defaults to empty dictionary."""
        notification = NotificationData(
            event_type="test",
            message="test",
        )

        assert notification.details == {}
        assert isinstance(notification.details, dict)

    def test_details_accepts_mixed_types(self) -> None:
        """Test that details can contain string, int, float, and None values."""
        details: dict[str, str | int | float | None] = {
            "string_value": "text",
            "int_value": 123,
            "float_value": 45.67,
            "none_value": None,
        }

        notification = NotificationData(
            event_type="test",
            message="test",
            details=details,
        )

        assert notification.details == details

    def test_model_serialization(self) -> None:
        """Test that NotificationData can be serialized to dict."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        notification = NotificationData(
            event_type="test_event",
            timestamp=timestamp,
            message="Test message",
            details={"key": "value"},
        )

        data = notification.model_dump()

        assert data["event_type"] == "test_event"
        assert data["timestamp"] == timestamp
        assert data["message"] == "Test message"
        assert data["details"] == {"key": "value"}

    def test_model_json_serialization(self) -> None:
        """Test that NotificationData can be serialized to JSON."""
        notification = NotificationData(
            event_type="test_event",
            message="Test message",
            details={"key": "value"},
        )

        json_str = notification.model_dump_json()

        assert "test_event" in json_str
        assert "Test message" in json_str
        assert "key" in json_str
