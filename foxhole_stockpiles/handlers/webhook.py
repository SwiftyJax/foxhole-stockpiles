"""Webhook output handler - sends data to webhook endpoint."""

import logging
from typing import Any

from foxhole_stockpiles.connectors.webhook import WebhookConnector
from foxhole_stockpiles.core.settings.sections.output import WebhookOutputSettings
from foxhole_stockpiles.handlers.base_handler import BaseOutputDestinationHandler
from foxhole_stockpiles.models.stockpile import Stockpile


class WebhookOutputHandler(BaseOutputDestinationHandler):
    """Handles sending stockpile data to webhook endpoints."""

    def __init__(self, webhook_settings: WebhookOutputSettings) -> None:
        """Initialize webhook output handler.

        Args:
            webhook_settings (WebhookOutputSettings): Webhook configuration settings
        """
        self.logger = logging.getLogger(__name__)
        self.webhook_settings = webhook_settings

    async def handle(self, stockpile: Stockpile, **kwargs: Any) -> dict[str, Any]:
        """Send stockpile data to webhook endpoint.

        Args:
            stockpile (Stockpile): The stockpile data to send
            **kwargs: Additional parameters:
                - token (str | None): Optional auth token to override configured token

        Returns:
            dict[str, Any]: Webhook response data

        Raises:
            ValueError: If webhook URL is not configured
        """
        if not self.webhook_settings.url:
            raise ValueError("Webhook URL is not configured")

        webhook_connector = WebhookConnector(self.webhook_settings)
        payload = stockpile.model_dump(mode="json")
        token = kwargs.get("token")

        response = await webhook_connector.send_stockpile(payload=payload, token=token)
        self.logger.debug("Webhook response: %s", response)
        return response
