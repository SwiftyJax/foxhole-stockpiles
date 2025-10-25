"""Output coordinator for managing different output destinations."""

import logging
from typing import Any

from foxhole_stockpiles.core.settings import AppSettings
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.handlers.console import ConsoleOutputHandler
from foxhole_stockpiles.handlers.file import FileOutputHandler
from foxhole_stockpiles.handlers.response import ReturnOutputHandler
from foxhole_stockpiles.handlers.webhook import WebhookOutputHandler
from foxhole_stockpiles.models.stockpile import Stockpile


class OutputCoordinator:
    """Coordinates output handling by delegating to specific destination handlers."""

    def __init__(self, settings: AppSettings) -> None:
        """Initialize output coordinator with application settings.

        Args:
            settings (AppSettings): Application settings containing output configuration
        """
        self.settings = settings
        self.logger = logging.getLogger(__name__)

        # Initialize destination handlers
        self._handlers = {
            OutputDestination.RETURN: ReturnOutputHandler(),
            OutputDestination.FILE: FileOutputHandler(default_file_path=settings.output.file.path),
            OutputDestination.WEBHOOK: WebhookOutputHandler(
                webhook_settings=settings.output.webhook
            ),
            OutputDestination.CONSOLE: ConsoleOutputHandler(),
        }

    async def handle_output(
        self,
        stockpile: Stockpile,
        destination: OutputDestination,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Handle output based on the specified destination.

        Args:
            stockpile (Stockpile): The stockpile data to output
            destination (OutputDestination): The desired output destination
            **kwargs: Additional destination-specific parameters (e.g., token, file_path)

        Returns:
            dict[str, Any] | None: Response data if applicable (RETURN, WEBHOOK), None otherwise

        Raises:
            ValueError: If destination is not supported
        """
        handler = self._handlers.get(destination)

        if not handler:
            raise ValueError(f"Unsupported output destination: {destination}")

        self.logger.debug("Handling output with destination: %s", destination)
        return await handler.handle(stockpile, **kwargs)
