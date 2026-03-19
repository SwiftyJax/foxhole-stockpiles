"""Tests for BaseOutputDestinationHandler."""

from typing import Any

import pytest

from foxhole_stockpiles.handlers.base_handler import BaseOutputDestinationHandler
from foxhole_stockpiles.models.stockpile import Stockpile


class TestBaseOutputDestinationHandler:
    """Tests for BaseOutputDestinationHandler abstract class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseOutputDestinationHandler()  # type: ignore[abstract]

    def test_subclass_must_implement_handle(self) -> None:
        """Test that subclass must implement handle method."""

        class IncompleteHandler(BaseOutputDestinationHandler):
            """Handler that doesn't implement handle()."""

            pass

        with pytest.raises(TypeError):
            IncompleteHandler()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_concrete_subclass_works(self) -> None:
        """Test that concrete subclass can be instantiated and used."""
        from foxhole_stockpiles.enums.stockpile_type import StockpileType

        class ConcreteHandler(BaseOutputDestinationHandler):
            """Concrete handler implementation."""

            async def handle(self, stockpile: Stockpile, **kwargs: Any) -> dict[str, Any] | None:
                """Handle output."""
                return {"handled": True, "name": stockpile.name}

        handler = ConcreteHandler()
        stockpile = Stockpile(
            name="Test",
            type=StockpileType.STORAGE_DEPOT,
            items=[],
        )

        result = await handler.handle(stockpile)

        assert result is not None
        assert result["handled"] is True
        assert result["name"] == "Test"
