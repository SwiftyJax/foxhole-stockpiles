"""Output handler for managing different output formats."""

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any

from foxhole_stockpiles.connectors.webhook import WebhookConnector
from foxhole_stockpiles.core.settings import AppSettings
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.models.stockpile import Stockpile


class OutputHandler:
    """Handles output formatting and delivery for stockpile results."""

    def __init__(self, settings: AppSettings) -> None:
        """Initialize output handler with application settings.

        Args:
            settings (AppSettings): Application settings containing output configuration
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def handle_output(
        self, stockpile: Stockpile, output_format: OutputFormat, token: str | None = None
    ) -> dict[str, Any] | None:
        """Handle output based on the specified format.

        Args:
            stockpile (Stockpile): The stockpile data to output
            output_format (OutputFormat): The desired output format
            token (str | None): Optional token to override the configured webhook token

        Returns:
            dict[str, Any] | None: JSON data if format is JSON, webhook response if webhook,
                None otherwise
        """
        match output_format:
            case OutputFormat.CONSOLE:
                self._output_console(stockpile=stockpile)
                return None
            case OutputFormat.JSON:
                return stockpile.model_dump(mode="json")
            case OutputFormat.FILE:
                self._output_file(stockpile=stockpile)
                return None
            case OutputFormat.WEBHOOK:
                return self._output_webhook(stockpile=stockpile, token=token)

    def _output_console(self, stockpile: Stockpile) -> None:
        """Output stockpile data to console.

        Args:
            stockpile (Stockpile): The stockpile data to output
        """
        self.logger.info("Name: %s", stockpile.name)
        self.logger.info("Type: %s", stockpile.type.value)
        self.logger.info("Hex: %s", stockpile.hex_name)
        self.logger.info("Shard: %s", stockpile.shard)
        self.logger.info("Ingame timestamp: %s", stockpile.ingame_timestamp)
        self.logger.info("Items:")
        for item in stockpile.items:
            code = item.code
            if item.crated:
                code += "_crated"
            self.logger.info(
                "* code: %-35s quantity: %-3d, confidence: %.3f",
                code,
                item.quantity,
                item.confidence or 0.0,
            )

    def _output_file(self, stockpile: Stockpile) -> None:
        """Output stockpile data to file.

        Args:
            stockpile (Stockpile): The stockpile data to output
        """
        file = self.settings.output_format.file_path
        if not file:
            file = "output.json"

        if "{timestamp}" in file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file = file.replace("{timestamp}", timestamp)

        output_path = Path(file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            f.write(stockpile.model_dump_json())

        self.logger.info("Output saved to: %s", output_path)

    def _output_webhook(self, stockpile: Stockpile, token: str | None = None) -> dict[str, Any]:
        """Output stockpile data via webhook.

        Args:
            stockpile (Stockpile): The stockpile data to output
            token (str | None): Optional token to override the configured webhook token

        Returns:
            dict[str, Any]: Webhook response data

        Raises:
            ValueError: If webhook URL is not configured
        """
        if not self.settings.output_format.webhook_url:
            raise ValueError("Webhook URL is not set in the configuration")

        webhook_connector = WebhookConnector(self.settings.output_format)
        if not webhook_connector:
            raise ValueError("Failed to initialize Webhook connector")

        payload = stockpile.model_dump(mode="json")
        response = asyncio.run(webhook_connector.send_stockpile(payload=payload, token=token))
        self.logger.info("Webhook response: %s", response)
        return response
