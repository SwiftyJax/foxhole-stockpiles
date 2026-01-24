"""Tests for api.dependencies module."""

from unittest.mock import Mock, patch

import pytest

from foxhole_stockpiles.api.dependencies import (
    clear_dependency_caches,
    get_event_bus_dependency,
    get_notification_service,
    get_ocr_coordinator,
    get_output_coordinator,
)
from foxhole_stockpiles.core.events import EventBus
from foxhole_stockpiles.services.notification_service import NotificationService


class TestGetNotificationService:
    """Test suite for get_notification_service dependency."""

    def test_get_notification_service_returns_singleton(self) -> None:
        """Test that get_notification_service returns the same instance."""
        # Clear the cache first
        get_notification_service.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch("foxhole_stockpiles.api.dependencies.get_event_bus") as mock_event_bus:
                mock_settings.return_value.notifications.enabled = False
                mock_event_bus.return_value = EventBus()

                service1 = get_notification_service()
                service2 = get_notification_service()

                assert service1 is service2
                assert isinstance(service1, NotificationService)

        get_notification_service.cache_clear()

    def test_get_notification_service_initializes_service(self) -> None:
        """Test that get_notification_service initializes the service."""
        get_notification_service.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch("foxhole_stockpiles.api.dependencies.get_event_bus") as mock_event_bus:
                with patch(
                    "foxhole_stockpiles.api.dependencies.NotificationService"
                ) as mock_service_class:
                    mock_settings.return_value.notifications.enabled = False
                    mock_event_bus.return_value = EventBus()
                    mock_service = Mock()
                    mock_service_class.return_value = mock_service

                    result = get_notification_service()

                    mock_service.initialize.assert_called_once()
                    assert result is mock_service

        get_notification_service.cache_clear()


class TestGetEventBusDependency:
    """Test suite for get_event_bus_dependency."""

    def test_get_event_bus_dependency_returns_event_bus(self) -> None:
        """Test that get_event_bus_dependency returns the global event bus."""
        with patch("foxhole_stockpiles.api.dependencies.get_event_bus") as mock_get:
            mock_bus = EventBus()
            mock_get.return_value = mock_bus

            result = get_event_bus_dependency()

            assert result is mock_bus
            mock_get.assert_called_once()


class TestGetOCRCoordinator:
    """Test suite for get_ocr_coordinator dependency."""

    def test_get_ocr_coordinator_returns_singleton(self) -> None:
        """Test that get_ocr_coordinator returns the same instance."""
        get_ocr_coordinator.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch("foxhole_stockpiles.api.dependencies.get_event_bus") as mock_event_bus:
                with patch(
                    "foxhole_stockpiles.api.dependencies.OCRCoordinator"
                ) as mock_coordinator_class:
                    mock_settings.return_value.scanner.database_path = "/path/to/db.h5"
                    mock_event_bus.return_value = EventBus()
                    mock_coordinator = Mock()
                    mock_coordinator_class.return_value = mock_coordinator

                    coordinator1 = get_ocr_coordinator()
                    coordinator2 = get_ocr_coordinator()

                    assert coordinator1 is coordinator2
                    assert coordinator1 is mock_coordinator

        get_ocr_coordinator.cache_clear()

    def test_get_ocr_coordinator_raises_when_database_path_none(self) -> None:
        """Test that get_ocr_coordinator raises ValueError when database_path is None."""
        get_ocr_coordinator.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch("foxhole_stockpiles.api.dependencies.get_event_bus"):
                mock_settings.return_value.scanner.database_path = None

                with pytest.raises(ValueError, match="scanner.database_path must be configured"):
                    get_ocr_coordinator()

        get_ocr_coordinator.cache_clear()

    def test_get_ocr_coordinator_creates_with_correct_params(self) -> None:
        """Test that get_ocr_coordinator creates OCRCoordinator with correct parameters."""
        get_ocr_coordinator.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch("foxhole_stockpiles.api.dependencies.get_event_bus") as mock_event_bus:
                with patch(
                    "foxhole_stockpiles.api.dependencies.OCRCoordinator"
                ) as mock_coordinator_class:
                    mock_scanner_config = Mock()
                    mock_scanner_config.database_path = "/path/to/db.h5"
                    mock_settings.return_value.scanner = mock_scanner_config
                    mock_bus = EventBus()
                    mock_event_bus.return_value = mock_bus

                    get_ocr_coordinator()

                    mock_coordinator_class.assert_called_once_with(
                        config=mock_scanner_config, event_bus=mock_bus
                    )

        get_ocr_coordinator.cache_clear()


class TestGetOutputCoordinator:
    """Test suite for get_output_coordinator dependency."""

    def test_get_output_coordinator_returns_singleton(self) -> None:
        """Test that get_output_coordinator returns the same instance."""
        get_output_coordinator.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch(
                "foxhole_stockpiles.api.dependencies.OutputCoordinator"
            ) as mock_coordinator_class:
                mock_settings_obj = Mock()
                mock_settings.return_value = mock_settings_obj
                mock_coordinator = Mock()
                mock_coordinator_class.return_value = mock_coordinator

                coordinator1 = get_output_coordinator()
                coordinator2 = get_output_coordinator()

                assert coordinator1 is coordinator2
                assert coordinator1 is mock_coordinator

        get_output_coordinator.cache_clear()

    def test_get_output_coordinator_creates_with_settings(self) -> None:
        """Test that get_output_coordinator creates OutputCoordinator with output settings."""
        get_output_coordinator.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch(
                "foxhole_stockpiles.api.dependencies.OutputCoordinator"
            ) as mock_coordinator_class:
                mock_settings_obj = Mock()
                mock_settings.return_value = mock_settings_obj

                get_output_coordinator()

                mock_coordinator_class.assert_called_once_with(
                    output_settings=mock_settings_obj.output
                )

        get_output_coordinator.cache_clear()


class TestClearDependencyCaches:
    """Test suite for clear_dependency_caches function."""

    def test_clear_dependency_caches_shuts_down_notification_service(self) -> None:
        """Test that clear_dependency_caches calls shutdown on notification service."""
        # First, populate the notification service cache
        get_notification_service.cache_clear()

        with patch("foxhole_stockpiles.api.dependencies.get_settings") as mock_settings:
            with patch("foxhole_stockpiles.api.dependencies.get_event_bus") as mock_event_bus:
                mock_settings.return_value.notifications.enabled = False
                mock_event_bus.return_value = EventBus()

                service = get_notification_service()

                # Spy on the shutdown method
                with patch.object(service, "shutdown") as mock_shutdown:
                    # Clear caches
                    clear_dependency_caches()

                    # Verify shutdown was called
                    mock_shutdown.assert_called_once()

        get_notification_service.cache_clear()

    def test_clear_dependency_caches_handles_empty_cache(self) -> None:
        """Test that clear_dependency_caches handles case when no cache exists."""
        # Clear all caches first
        get_notification_service.cache_clear()
        get_ocr_coordinator.cache_clear()
        get_output_coordinator.cache_clear()

        # Should not raise any exception
        clear_dependency_caches()
