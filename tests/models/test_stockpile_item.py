"""Tests for models.stockpile_item module.

This module contains tests for the StockpileItem model,
including serialization and validation.
"""

import pytest

from foxhole_stockpiles.models.stockpile_item import StockpileItem


class TestStockpileItemCreation:
    """Test suite for StockpileItem creation and initialization."""

    def test_create_item_with_all_fields(self) -> None:
        """Test creating a StockpileItem with all fields."""
        item = StockpileItem(
            code="Rifle",
            quantity=10,
            crated=False,
            confidence=0.95,
        )

        assert item.code == "Rifle"
        assert item.quantity == 10
        assert item.crated is False
        assert item.confidence == 0.95

    def test_create_item_with_defaults(self) -> None:
        """Test creating a StockpileItem with default values."""
        item = StockpileItem(code="Rifle")

        assert item.code == "Rifle"
        assert item.quantity == -1  # Default
        assert item.crated is False  # Default
        assert item.confidence is None  # Default

    def test_create_item_with_crated_true(self) -> None:
        """Test creating a crated item."""
        item = StockpileItem(
            code="Rifle",
            crated=True,
        )

        assert item.crated is True

    def test_create_item_with_none_confidence(self) -> None:
        """Test creating an item with None confidence."""
        item = StockpileItem(
            code="Rifle",
            quantity=5,
            confidence=None,
        )

        assert item.confidence is None


class TestStockpileItemSerialization:
    """Test suite for StockpileItem serialization."""

    def test_serialize_confidence_with_none(self) -> None:
        """Test serializing confidence when value is None."""
        item = StockpileItem(
            code="Rifle",
            quantity=10,
            confidence=None,
        )

        # Test the serializer method directly
        serialized_confidence = item.serialize_confidence(None)
        assert serialized_confidence is None

        # Test JSON serialization
        data = item.model_dump()
        assert data["confidence"] is None

    def test_serialize_confidence_with_value(self) -> None:
        """Test serializing confidence with a value (rounds to 3 decimals)."""
        item = StockpileItem(
            code="Rifle",
            quantity=10,
            confidence=0.123456789,
        )

        # Test JSON serialization rounds to 3 decimals
        data = item.model_dump()
        assert data["confidence"] == 0.123

    def test_serialize_confidence_rounding(self) -> None:
        """Test confidence rounding in serialization."""
        item = StockpileItem(
            code="Rifle",
            quantity=10,
            confidence=0.9876,
        )

        data = item.model_dump()
        assert data["confidence"] == 0.988  # Rounded to 3 decimals

    def test_json_serialization_with_none_confidence(self) -> None:
        """Test full JSON serialization with None confidence."""
        item = StockpileItem(
            code="TestRifle",
            quantity=5,
            crated=False,
            confidence=None,
        )

        json_data = item.model_dump_json()
        assert '"confidence":null' in json_data

    def test_json_serialization_with_confidence(self) -> None:
        """Test full JSON serialization with confidence value."""
        item = StockpileItem(
            code="TestRifle",
            quantity=5,
            crated=False,
            confidence=0.95432,
        )

        json_data = item.model_dump_json()
        assert '"confidence":0.954' in json_data


class TestStockpileItemValidation:
    """Test suite for StockpileItem validation."""

    def test_confidence_validation_min(self) -> None:
        """Test confidence minimum value validation."""
        # 0.0 should be valid
        item = StockpileItem(code="Rifle", confidence=0.0)
        assert item.confidence == 0.0

        # Negative should fail
        with pytest.raises(ValueError):
            StockpileItem(code="Rifle", confidence=-0.1)

    def test_confidence_validation_max(self) -> None:
        """Test confidence maximum value validation."""
        # 1.0 should be valid
        item = StockpileItem(code="Rifle", confidence=1.0)
        assert item.confidence == 1.0

        # Greater than 1.0 should fail
        with pytest.raises(ValueError):
            StockpileItem(code="Rifle", confidence=1.1)

    def test_quantity_validation_min(self) -> None:
        """Test quantity minimum value validation."""
        # -1 should be valid (unknown quantity)
        item = StockpileItem(code="Rifle", quantity=-1)
        assert item.quantity == -1

        # Less than -1 should fail
        with pytest.raises(ValueError):
            StockpileItem(code="Rifle", quantity=-2)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError):
            StockpileItem(
                code="Rifle",
                quantity=10,
                extra_field="not_allowed",  # type: ignore
            )
