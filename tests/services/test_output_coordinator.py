"""Tests for output coordinator module.

This module contains comprehensive tests for the OutputCoordinator which orchestrates
output handling by delegating to specific destination handlers.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from foxhole_stockpiles.core.settings import (
    AppSettings,
    FileOutputSettings,
    OutputSettings,
    WebhookOutputSettings,
)
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_item import StockpileItem
from foxhole_stockpiles.services.output_coordinator import OutputCoordinator


@pytest.fixture
def sample_stockpile() -> Stockpile:
    """Create a sample stockpile for testing.

    Returns:
        Stockpile: A configured stockpile instance with test data for output testing.
    """
    items = [
        StockpileItem(quantity=100, code="BasicMaterialsIcon", confidence=0.95),
        StockpileItem(quantity=50, code="PetrolIcon", confidence=0.87),
        StockpileItem(quantity=75, code="DieselIcon", confidence=0.92),
    ]

    return Stockpile(
        name="Test Stockpile",
        type=StockpileType.SEAPORT,
        items=items,
        shard="TEST",
        ingame_timestamp="Day 1,000, 1000 Hours",
        resolution="1920x1080",
    )


@pytest.fixture
def app_settings() -> AppSettings:
    """Create app settings for testing.

    Returns:
        AppSettings: Configured app settings for testing.
    """
    return AppSettings(
        output=OutputSettings(
            format=OutputFormat.JSON,
            destination=OutputDestination.RETURN,
            file=FileOutputSettings(path="output.json"),
            webhook=WebhookOutputSettings(url=None),
        )
    )


@pytest.fixture
def output_coordinator(app_settings: AppSettings) -> OutputCoordinator:
    """Create an output coordinator instance.

    Args:
        app_settings (AppSettings): App settings fixture.

    Returns:
        OutputCoordinator: A configured output coordinator instance for testing.
    """
    return OutputCoordinator(app_settings)


class TestOutputCoordinator:
    """Test cases for OutputCoordinator.

    This class contains tests for the main OutputCoordinator class which delegates
    to specific destination handlers.
    """

    def test_output_coordinator_initialization(self, output_coordinator: OutputCoordinator) -> None:
        """Test output coordinator initialization.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
        """
        assert isinstance(output_coordinator, OutputCoordinator)
        assert output_coordinator.settings is not None
        assert len(output_coordinator._handlers) == 4  # 4 destination handlers

    @pytest.mark.asyncio
    async def test_handle_output_return(
        self, output_coordinator: OutputCoordinator, sample_stockpile: Stockpile
    ) -> None:
        """Test RETURN destination handling.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        result = await output_coordinator.handle_output(sample_stockpile, OutputDestination.RETURN)

        # Should return dict
        assert isinstance(result, dict)
        assert result["name"] == "Test Stockpile"
        assert result["type"] == "Seaport"
        assert len(result["items"]) == 3

    @pytest.mark.asyncio
    async def test_handle_output_console(
        self, output_coordinator: OutputCoordinator, sample_stockpile: Stockpile
    ) -> None:
        """Test CONSOLE destination handling.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        with patch.object(
            output_coordinator._handlers[OutputDestination.CONSOLE],
            "handle",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_console:
            result = await output_coordinator.handle_output(
                sample_stockpile, OutputDestination.CONSOLE
            )

            assert result is None
            mock_console.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_output_file(
        self, output_coordinator: OutputCoordinator, sample_stockpile: Stockpile
    ) -> None:
        """Test FILE destination handling.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        with patch.object(
            output_coordinator._handlers[OutputDestination.FILE],
            "handle",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_file:
            result = await output_coordinator.handle_output(
                sample_stockpile, OutputDestination.FILE
            )

            assert result is None
            mock_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_output_file_with_custom_path(
        self, output_coordinator: OutputCoordinator, sample_stockpile: Stockpile
    ) -> None:
        """Test FILE destination with custom file path.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        custom_path = Path("custom/output.json")

        with patch.object(
            output_coordinator._handlers[OutputDestination.FILE],
            "handle",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_file:
            result = await output_coordinator.handle_output(
                sample_stockpile, OutputDestination.FILE, file_path=custom_path
            )

            assert result is None
            mock_file.assert_called_once_with(sample_stockpile, file_path=custom_path)

    @pytest.mark.asyncio
    async def test_handle_output_webhook(
        self, output_coordinator: OutputCoordinator, sample_stockpile: Stockpile
    ) -> None:
        """Test WEBHOOK destination handling.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        webhook_response = {"status": "success", "id": "12345"}

        with patch.object(
            output_coordinator._handlers[OutputDestination.WEBHOOK],
            "handle",
            new_callable=AsyncMock,
        ) as mock_webhook:
            mock_webhook.return_value = webhook_response

            result = await output_coordinator.handle_output(
                sample_stockpile, OutputDestination.WEBHOOK
            )

            assert result == webhook_response
            mock_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_output_webhook_with_token(
        self, output_coordinator: OutputCoordinator, sample_stockpile: Stockpile
    ) -> None:
        """Test WEBHOOK destination with custom token.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        custom_token = "custom_token_123"
        webhook_response = {"status": "success", "id": "12345"}

        with patch.object(
            output_coordinator._handlers[OutputDestination.WEBHOOK],
            "handle",
            new_callable=AsyncMock,
        ) as mock_webhook:
            mock_webhook.return_value = webhook_response

            result = await output_coordinator.handle_output(
                sample_stockpile, OutputDestination.WEBHOOK, token=custom_token
            )

            assert result == webhook_response
            mock_webhook.assert_called_once_with(sample_stockpile, token=custom_token)

    @pytest.mark.asyncio
    async def test_unsupported_destination(
        self, output_coordinator: OutputCoordinator, sample_stockpile: Stockpile
    ) -> None:
        """Test handling of unsupported destination.

        Args:
            output_coordinator (OutputCoordinator): Output coordinator instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        # Manually remove a handler to simulate unsupported destination
        del output_coordinator._handlers[OutputDestination.FILE]

        with pytest.raises(ValueError, match="Unsupported output destination"):
            await output_coordinator.handle_output(sample_stockpile, OutputDestination.FILE)
