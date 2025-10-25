"""Base output destination handler interface."""

from abc import ABC, abstractmethod
from typing import Any

from foxhole_stockpiles.models.stockpile import Stockpile


class BaseOutputDestinationHandler(ABC):
    """Abstract base class for output destination handlers."""

    @abstractmethod
    async def handle(self, stockpile: Stockpile, **kwargs: Any) -> dict[str, Any] | None:
        """Handle output to the destination.

        Args:
            stockpile (Stockpile): The stockpile data to output
            **kwargs: Additional destination-specific parameters

        Returns:
            dict[str, Any] | None: Optional response data from the destination
        """
        pass
