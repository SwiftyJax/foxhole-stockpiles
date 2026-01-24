"""Tests for individual output handler implementations.

This module contains tests for specific output destination handlers:
ConsoleOutputHandler, ReturnOutputHandler, FileOutputHandler, and WebhookOutputHandler.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from foxhole_stockpiles.core.settings.sections.output import (
    WebhookHandlerSettings,
)
from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.handlers.console import ConsoleOutputHandler
from foxhole_stockpiles.handlers.file import FileOutputHandler
from foxhole_stockpiles.handlers.response import ReturnOutputHandler
from foxhole_stockpiles.handlers.webhook import WebhookOutputHandler
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_item import StockpileItem


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


class TestConsoleOutputHandler:
    """Test cases for ConsoleOutputHandler."""

    @pytest.mark.asyncio
    async def test_console_output(self, sample_stockpile: Stockpile) -> None:
        """Test console output method.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        handler = ConsoleOutputHandler()

        with patch.object(handler.logger, "info") as mock_logger:
            await handler.handle(sample_stockpile)

            # Verify logger calls
            mock_logger.assert_any_call("Name: %s", "Test Stockpile")
            mock_logger.assert_any_call("Type: %s", "Seaport")
            mock_logger.assert_any_call("Shard: %s", "TEST")


class TestReturnOutputHandler:
    """Test cases for ReturnOutputHandler."""

    @pytest.mark.asyncio
    async def test_return_output(self, sample_stockpile: Stockpile) -> None:
        """Test return output handler.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        handler = ReturnOutputHandler()
        result = await handler.handle(sample_stockpile)

        assert isinstance(result, dict)
        assert result["name"] == "Test Stockpile"
        assert result["type"] == "Seaport"
        assert len(result["items"]) == 3


class TestFileOutputHandler:
    """Test cases for FileOutputHandler."""

    @pytest.mark.asyncio
    async def test_file_output_default_path(self, sample_stockpile: Stockpile) -> None:
        """Test file output with default path.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        handler = FileOutputHandler(default_file_path="output.json")

        with patch("pathlib.Path.open") as mock_open, patch("pathlib.Path.mkdir"):
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await handler.handle(sample_stockpile)

            mock_file.write.assert_called_once()
            written_data = mock_file.write.call_args[0][0]
            data = json.loads(written_data)
            assert data["name"] == "Test Stockpile"

    @pytest.mark.asyncio
    async def test_file_output_custom_path(self, sample_stockpile: Stockpile) -> None:
        """Test file output with custom path.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        handler = FileOutputHandler()
        custom_path = Path("custom/output.json")

        with patch("pathlib.Path.open") as mock_open, patch("pathlib.Path.mkdir"):
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await handler.handle(sample_stockpile, file_path=custom_path)

            mock_file.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_output_with_timestamp(self, sample_stockpile: Stockpile) -> None:
        """Test file output with timestamp placeholder.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        handler = FileOutputHandler(default_file_path="output_{timestamp}.json")

        with (
            patch("pathlib.Path.open") as mock_open,
            patch("pathlib.Path.mkdir"),
            patch("datetime.datetime") as mock_datetime,
        ):
            mock_datetime.now.return_value.strftime.return_value = "20240104_090000"
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await handler.handle(sample_stockpile)

            mock_file.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_output_no_path(self, sample_stockpile: Stockpile) -> None:
        """Test file output raises error when no path provided.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        handler = FileOutputHandler()

        with pytest.raises(ValueError, match="File path must be provided"):
            await handler.handle(sample_stockpile)


class TestWebhookOutputHandler:
    """Test cases for WebhookOutputHandler."""

    @pytest.mark.asyncio
    async def test_webhook_output_success(self, sample_stockpile: Stockpile) -> None:
        """Test successful webhook output.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        webhook_settings = WebhookHandlerSettings(url="https://example.com/webhook")
        webhook_response = {"status": "success", "id": "12345"}

        with patch("foxhole_stockpiles.handlers.webhook.WebhookConnector") as mock_connector_class:
            mock_connector = Mock()
            mock_connector.send_stockpile = AsyncMock(return_value=webhook_response)
            mock_connector_class.return_value = mock_connector

            handler = WebhookOutputHandler(webhook_settings=webhook_settings)
            result = await handler.handle(sample_stockpile)

            assert result == webhook_response
            mock_connector.send_stockpile.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_output_with_token(self, sample_stockpile: Stockpile) -> None:
        """Test webhook output with custom token.

        Args:
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        webhook_settings = WebhookHandlerSettings(url="https://example.com/webhook")
        custom_token = "custom_token_123"
        webhook_response = {"status": "success", "id": "12345"}

        with patch("foxhole_stockpiles.handlers.webhook.WebhookConnector") as mock_connector_class:
            mock_connector = Mock()
            mock_connector.send_stockpile = AsyncMock(return_value=webhook_response)
            mock_connector_class.return_value = mock_connector

            handler = WebhookOutputHandler(webhook_settings=webhook_settings)
            result = await handler.handle(sample_stockpile, token=custom_token)

            assert result == webhook_response
            mock_connector.send_stockpile.assert_called_once_with(
                payload=sample_stockpile.model_dump(mode="json"), token=custom_token
            )
