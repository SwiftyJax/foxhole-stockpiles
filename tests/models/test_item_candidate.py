"""Tests for models.item_candidate module.

This module contains tests for the ItemCandidate model,
including serialization and validation.
"""

import pytest

from foxhole_stockpiles.models.item_candidate import ItemCandidate


class TestItemCandidateCreation:
    """Test suite for ItemCandidate creation and initialization."""

    def test_create_candidate_with_all_fields(self) -> None:
        """Test creating an ItemCandidate with all fields."""
        candidate = ItemCandidate(code="RifleAlt", confidence=0.92)

        assert candidate.code == "RifleAlt"
        assert candidate.confidence == 0.92

    def test_create_candidate_boundary_values(self) -> None:
        """Test creating candidates with boundary confidence values."""
        candidate_min = ItemCandidate(code="Item1", confidence=0.0)
        assert candidate_min.confidence == 0.0

        candidate_max = ItemCandidate(code="Item2", confidence=1.0)
        assert candidate_max.confidence == 1.0


class TestItemCandidateSerialization:
    """Test suite for ItemCandidate serialization."""

    def test_serialize_confidence_rounding(self) -> None:
        """Test confidence rounding in serialization."""
        candidate = ItemCandidate(code="RifleAlt", confidence=0.923456789)

        data = candidate.model_dump()
        assert data["confidence"] == 0.923

    def test_json_serialization(self) -> None:
        """Test full JSON serialization."""
        candidate = ItemCandidate(code="RifleAlt", confidence=0.9234)

        json_data = candidate.model_dump_json()
        assert '"code":"RifleAlt"' in json_data
        assert '"confidence":0.923' in json_data


class TestItemCandidateValidation:
    """Test suite for ItemCandidate validation."""

    def test_confidence_below_minimum(self) -> None:
        """Test that confidence below 0.0 raises error."""
        with pytest.raises(ValueError):
            ItemCandidate(code="Item", confidence=-0.1)

    def test_confidence_above_maximum(self) -> None:
        """Test that confidence above 1.0 raises error."""
        with pytest.raises(ValueError):
            ItemCandidate(code="Item", confidence=1.1)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError):
            ItemCandidate(
                code="Item",
                confidence=0.9,
                extra_field="not_allowed",  # type: ignore
            )
