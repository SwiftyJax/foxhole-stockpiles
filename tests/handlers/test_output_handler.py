"""Tests for output handler module.

This module contains comprehensive tests for the output handler system,
including output formatting and delivery in various formats.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from foxhole_stockpiles.core.settings import AppSettings, OutputFormatSettings
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.handlers.output_handler import OutputHandler
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


@pytest.fixture
def app_settings() -> AppSettings:
    """Create app settings for testing.

    Returns:
        AppSettings: Configured app settings for testing.
    """
    return AppSettings(
        output_format=OutputFormatSettings(
            output_format=OutputFormat.JSON,
            file_path="output.json",
        )
    )


@pytest.fixture
def output_handler(app_settings: AppSettings) -> OutputHandler:
    """Create an output handler instance.

    Args:
        app_settings (AppSettings): App settings fixture.

    Returns:
        OutputHandler: A configured output handler instance for testing.
    """
    return OutputHandler(app_settings)


class TestOutputHandler:
    """Test cases for OutputHandler.

    This class contains tests for the OutputHandler class which handles
    formatting and outputting stockpile data in various formats.
    """

    def test_output_handler_initialization(self, output_handler: OutputHandler) -> None:
        """Test output handler initialization.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
        """
        assert isinstance(output_handler, OutputHandler)
        assert output_handler.settings is not None

    @pytest.mark.asyncio
    async def test_handle_output_json(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test JSON output handling.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        result = await output_handler.handle_output(sample_stockpile, OutputFormat.JSON)

        # Should return dict
        assert isinstance(result, dict)
        assert result["name"] == "Test Stockpile"
        assert result["type"] == "Seaport"
        assert len(result["items"]) == 3

    @pytest.mark.asyncio
    async def test_handle_output_console(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test console output handling.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        with patch.object(output_handler, "_output_console") as mock_console:
            result = await output_handler.handle_output(sample_stockpile, OutputFormat.CONSOLE)

            assert result is None
            mock_console.assert_called_once_with(stockpile=sample_stockpile)

    @pytest.mark.asyncio
    async def test_handle_output_file(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test file output handling.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        with patch.object(output_handler, "_output_file", new_callable=AsyncMock) as mock_file:
            result = await output_handler.handle_output(sample_stockpile, OutputFormat.FILE)

            assert result is None
            mock_file.assert_called_once_with(stockpile=sample_stockpile)

    @pytest.mark.asyncio
    async def test_handle_output_webhook(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test webhook output handling.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        webhook_response = {"status": "success", "id": "12345"}

        with patch.object(
            output_handler, "_output_webhook", new_callable=AsyncMock
        ) as mock_webhook:
            mock_webhook.return_value = webhook_response

            result = await output_handler.handle_output(sample_stockpile, OutputFormat.WEBHOOK)

            assert result == webhook_response
            mock_webhook.assert_called_once_with(stockpile=sample_stockpile, token=None)

    @pytest.mark.asyncio
    async def test_handle_output_webhook_with_token(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test webhook output handling with custom token.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        custom_token = "custom_token_123"
        webhook_response = {"status": "success", "id": "12345"}

        with patch.object(
            output_handler, "_output_webhook", new_callable=AsyncMock
        ) as mock_webhook:
            mock_webhook.return_value = webhook_response

            result = await output_handler.handle_output(
                sample_stockpile, OutputFormat.WEBHOOK, token=custom_token
            )

            assert result == webhook_response
            mock_webhook.assert_called_once_with(stockpile=sample_stockpile, token=custom_token)

    def test_output_console(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test console output method.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        with patch.object(output_handler.logger, "info") as mock_logger:
            output_handler._output_console(sample_stockpile)

            # Verify logger calls
            mock_logger.assert_any_call("Name: %s", "Test Stockpile")
            mock_logger.assert_any_call("Type: %s", "Seaport")
            mock_logger.assert_any_call("Shard: %s", "TEST")

    @pytest.mark.asyncio
    async def test_output_file_default_name(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test file output with default filename.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        # Set file_path to empty string to test default behavior
        output_handler.settings.output_format.file_path = ""

        with patch("pathlib.Path.open") as mock_open, patch("pathlib.Path.mkdir"):
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await output_handler._output_file(sample_stockpile)

            mock_file.write.assert_called_once()
            written_data = mock_file.write.call_args[0][0]
            data = json.loads(written_data)
            assert data["name"] == "Test Stockpile"

    @pytest.mark.asyncio
    async def test_output_file_with_timestamp(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test file output with timestamp in filename.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        # Set file_path with timestamp placeholder
        output_handler.settings.output_format.file_path = "output_{timestamp}.json"

        with (
            patch("pathlib.Path.open") as mock_open,
            patch("pathlib.Path.mkdir"),
            patch("datetime.datetime") as mock_datetime,
        ):
            mock_datetime.now.return_value.strftime.return_value = "20240104_090000"
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await output_handler._output_file(sample_stockpile)

            mock_file.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_output_file_creates_directory(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test that file output creates parent directories.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        output_handler.settings.output_format.file_path = "subdir/output.json"

        with patch("pathlib.Path.open") as mock_open, patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await output_handler._output_file(sample_stockpile)

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.asyncio
    async def test_output_webhook_success(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test successful webhook output.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        # Configure webhook URL
        output_handler.settings.output_format.webhook_url = "https://example.com/webhook"

        webhook_response = {"status": "success", "id": "12345"}

        with patch(
            "foxhole_stockpiles.handlers.output_handler.WebhookConnector"
        ) as mock_connector_class:
            mock_connector = Mock()
            mock_connector.send_stockpile = AsyncMock(return_value=webhook_response)
            mock_connector_class.return_value = mock_connector

            result = await output_handler._output_webhook(sample_stockpile)

            assert result == webhook_response
            mock_connector.send_stockpile.assert_called_once()

    @pytest.mark.asyncio
    async def test_output_webhook_no_url_configured(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test webhook output when URL is not configured.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        # Ensure webhook URL is not set
        output_handler.settings.output_format.webhook_url = None

        with pytest.raises(ValueError, match="Webhook URL is not set"):
            await output_handler._output_webhook(sample_stockpile)

    @pytest.mark.asyncio
    async def test_output_webhook_with_custom_token(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test webhook output with custom token.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        # Configure webhook URL
        output_handler.settings.output_format.webhook_url = "https://example.com/webhook"
        custom_token = "custom_token_123"
        webhook_response = {"status": "success", "id": "12345"}

        with patch(
            "foxhole_stockpiles.handlers.output_handler.WebhookConnector"
        ) as mock_connector_class:
            mock_connector = Mock()
            mock_connector.send_stockpile = AsyncMock(return_value=webhook_response)
            mock_connector_class.return_value = mock_connector

            result = await output_handler._output_webhook(sample_stockpile, token=custom_token)

            assert result == webhook_response
            mock_connector.send_stockpile.assert_called_once_with(
                payload=sample_stockpile.model_dump(mode="json"), token=custom_token
            )

    @pytest.mark.asyncio
    async def test_output_webhook_connector_initialization_failure(
        self, output_handler: OutputHandler, sample_stockpile: Stockpile
    ) -> None:
        """Test webhook output when connector initialization fails.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
            sample_stockpile (Stockpile): Sample stockpile data from fixture.
        """
        # Configure webhook URL
        output_handler.settings.output_format.webhook_url = "https://example.com/webhook"

        with patch(
            "foxhole_stockpiles.handlers.output_handler.WebhookConnector", return_value=None
        ):
            with pytest.raises(ValueError, match="Failed to initialize Webhook connector"):
                await output_handler._output_webhook(sample_stockpile)

    def test_empty_stockpile_handling(self, output_handler: OutputHandler) -> None:
        """Test handling of empty stockpile.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
        """
        empty_stockpile = Stockpile(
            name="Empty",
            type=StockpileType.SEAPORT,
            items=[],
            shard="TEST",
        )

        with patch.object(output_handler.logger, "info") as mock_logger:
            output_handler._output_console(empty_stockpile)

            mock_logger.assert_any_call("Name: %s", "Empty")
            mock_logger.assert_any_call("Items:")

    def test_stockpile_with_errors_handling(self, output_handler: OutputHandler) -> None:
        """Test handling of stockpile with errors.

        Args:
            output_handler (OutputHandler): Output handler instance from fixture.
        """
        stockpile_with_errors = Stockpile(
            name="Error Test",
            type=StockpileType.SEAPORT,
            shard="TEST",
            items=[],
            errors=["Template matching failed", "OCR failed for position (100, 200)"],
        )

        with patch.object(output_handler.logger, "info") as mock_logger:
            output_handler._output_console(stockpile_with_errors)

            mock_logger.assert_any_call("Name: %s", "Error Test")
