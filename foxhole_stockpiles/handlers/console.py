"""Console output handler - prints data to stdout."""

import logging
from typing import Any

from foxhole_stockpiles.handlers.base_handler import BaseOutputDestinationHandler
from foxhole_stockpiles.models.stockpile import Stockpile


class ConsoleOutputHandler(BaseOutputDestinationHandler):
    """Handles printing stockpile data to console."""

    def __init__(self) -> None:
        """Initialize console output handler."""
        self.logger = logging.getLogger(__name__)

    async def handle(self, stockpiles: list[Stockpile], **kwargs: Any) -> None:
        """Print stockpile data to console.

        Prints each stockpile separately for readability.

        Args:
            stockpiles (list[Stockpile]): The stockpile data to print
            **kwargs: Additional parameters (unused)
        """
        for i, stockpile in enumerate(stockpiles):
            if i > 0:
                self.logger.info("---")  # Separator between stockpiles
            self._print_stockpile(stockpile)

    def _print_stockpile(self, stockpile: Stockpile) -> None:
        """Print a single stockpile to console.

        Args:
            stockpile (Stockpile): The stockpile data to print
        """
        self.logger.info("Name: %s", stockpile.name)
        self.logger.info("Type: %s", stockpile.type)
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
