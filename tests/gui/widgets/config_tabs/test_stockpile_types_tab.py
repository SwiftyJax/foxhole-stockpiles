"""Tests for StockpileTypesTab."""

from typing import Any

import pytest

from foxhole_stockpiles.core.settings.sections.stockpile_types import StockpileTypesSettings
from foxhole_stockpiles.gui.widgets.config_tabs.stockpile_types_tab import StockpileTypesTab
from foxhole_stockpiles.i18n import t


@pytest.fixture
def stockpile_types_tab(qtbot: Any) -> StockpileTypesTab:
    """Create a StockpileTypesTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        StockpileTypesTab: Tab instance
    """
    tab = StockpileTypesTab()
    qtbot.addWidget(tab)
    return tab


def test_stockpile_types_tab_initialization(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test StockpileTypesTab initialization.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    # Should have all 12 input fields (excluding undefined)
    assert len(stockpile_types_tab._inputs) == 12

    # Check all expected fields exist
    expected_fields = [
        "encampment",
        "keep",
        "safe_house",
        "relic_base",
        "bunker_base",
        "border_base",
        "town_base",
        "underground_fortress",
        "bms_longhook",
        "storage_depot",
        "seaport",
        "aircraft_depot",
    ]
    for field in expected_fields:
        assert field in stockpile_types_tab._inputs


def test_stockpile_types_tab_default_values(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test default values are empty.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    # All inputs should be empty by default
    for field_name, line_edit in stockpile_types_tab._inputs.items():
        assert line_edit.text() == "", f"Field {field_name} should be empty"


def test_stockpile_types_tab_set_values(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test setting values from settings object.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    settings = StockpileTypesSettings(
        seaport=["seapon", "Seapont"],
        storage_depot=["Storage Depo"],
        encampment=["Encampmnt"],
    )

    stockpile_types_tab.set_values(settings)

    assert stockpile_types_tab._inputs["seaport"].text() == "seapon, Seapont"
    assert stockpile_types_tab._inputs["storage_depot"].text() == "Storage Depo"
    assert stockpile_types_tab._inputs["encampment"].text() == "Encampmnt"
    # Other fields should remain empty
    assert stockpile_types_tab._inputs["keep"].text() == ""


def test_stockpile_types_tab_set_values_empty(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test setting empty values.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    settings = StockpileTypesSettings()

    stockpile_types_tab.set_values(settings)

    # All inputs should be empty
    for field_name, line_edit in stockpile_types_tab._inputs.items():
        assert line_edit.text() == "", f"Field {field_name} should be empty"


def test_stockpile_types_tab_get_values(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test getting values from widgets.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    stockpile_types_tab._inputs["seaport"].setText("seapon, Seapont")
    stockpile_types_tab._inputs["storage_depot"].setText("Storage Depo")

    settings = stockpile_types_tab.get_values()

    assert settings.seaport == ["seapon", "Seapont"]
    assert settings.storage_depot == ["Storage Depo"]
    assert settings.encampment == []  # Empty field


def test_stockpile_types_tab_get_values_empty(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test getting values when all fields are empty.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    settings = stockpile_types_tab.get_values()

    assert settings.seaport == []
    assert settings.storage_depot == []
    assert settings.encampment == []
    assert settings.keep == []
    assert settings.safe_house == []
    assert settings.relic_base == []
    assert settings.bunker_base == []
    assert settings.border_base == []
    assert settings.town_base == []
    assert settings.bms_longhook == []


def test_stockpile_types_tab_get_values_whitespace_handling(
    stockpile_types_tab: StockpileTypesTab,
) -> None:
    """Test that whitespace is properly stripped from values.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    # Test various whitespace scenarios
    stockpile_types_tab._inputs["seaport"].setText("  seapon  ,  Seapont  ,  ")

    settings = stockpile_types_tab.get_values()

    # Values should be trimmed and empty entries removed
    assert settings.seaport == ["seapon", "Seapont"]


def test_stockpile_types_tab_get_values_empty_commas(
    stockpile_types_tab: StockpileTypesTab,
) -> None:
    """Test that empty entries between commas are ignored.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    stockpile_types_tab._inputs["seaport"].setText("seapon,,Seapont,,,")

    settings = stockpile_types_tab.get_values()

    assert settings.seaport == ["seapon", "Seapont"]


def test_stockpile_types_tab_roundtrip(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test that setting and getting values preserves data.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    original_settings = StockpileTypesSettings(
        seaport=["seapon", "Seapont", "5eaport"],
        storage_depot=["Storage Depo", "Slorage Depot"],
        bunker_base=["Bunker Bose"],
    )

    stockpile_types_tab.set_values(original_settings)
    retrieved_settings = stockpile_types_tab.get_values()

    assert retrieved_settings.seaport == original_settings.seaport
    assert retrieved_settings.storage_depot == original_settings.storage_depot
    assert retrieved_settings.bunker_base == original_settings.bunker_base
    assert retrieved_settings.encampment == []


def test_stockpile_types_tab_placeholder_text(stockpile_types_tab: StockpileTypesTab) -> None:
    """Test that placeholder text is set on inputs.

    Args:
        stockpile_types_tab: StockpileTypesTab instance
    """
    expected_placeholder = t("stockpile_types_tab.alias_placeholder")
    for line_edit in stockpile_types_tab._inputs.values():
        assert line_edit.placeholderText() == expected_placeholder
