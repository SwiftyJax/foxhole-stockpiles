"""Tests for services.savefile_converter module."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.services.savefile_converter import SaveFileConverter


class TestSaveFileConverterInit:
    """Test suite for SaveFileConverter initialization."""

    def test_init_with_explicit_path(self, tmp_path: Path) -> None:
        """Test initializing with explicit uesave path."""
        uesave_path = tmp_path / "uesave"
        uesave_path.touch()

        converter = SaveFileConverter(uesave_path=uesave_path)
        assert converter._uesave_path == uesave_path

    def test_init_with_path_in_system(self) -> None:
        """Test initializing when uesave is in PATH."""
        with patch("shutil.which", return_value="/usr/bin/uesave"):
            converter = SaveFileConverter()
            assert converter._uesave_path == Path("/usr/bin/uesave")

    def test_init_raises_when_not_found(self) -> None:
        """Test that FileNotFoundError is raised when uesave not found."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="uesave not found"):
                SaveFileConverter()


class TestParseUETimestamp:
    """Test suite for UE timestamp parsing."""

    @pytest.fixture
    def converter(self) -> SaveFileConverter:
        """Create a converter instance."""
        with patch("shutil.which", return_value="/usr/bin/uesave"):
            return SaveFileConverter()

    def test_parse_zero_timestamp(self, converter: SaveFileConverter) -> None:
        """Test parsing zero timestamp returns current time."""
        result = converter._parse_ue_timestamp(0)
        assert result.tzinfo is not None
        # Should be close to now
        delta = abs((datetime.now(tz=UTC) - result).total_seconds())
        assert delta < 5

    def test_parse_valid_timestamp(self, converter: SaveFileConverter) -> None:
        """Test parsing a valid UE timestamp."""
        # Known timestamp: 638763313200000000 ticks = ~2025-02-05 UTC
        ticks = 638763313200000000
        result = converter._parse_ue_timestamp(ticks)
        assert result.year == 2025
        assert result.month == 2
        assert result.tzinfo is not None

    def test_parse_invalid_timestamp(self, converter: SaveFileConverter) -> None:
        """Test parsing invalid timestamp returns current time."""
        # Extremely large invalid ticks
        result = converter._parse_ue_timestamp(10**30)
        delta = abs((datetime.now(tz=UTC) - result).total_seconds())
        assert delta < 5


class TestParseStockpileItems:
    """Test suite for parsing stockpile items."""

    @pytest.fixture
    def converter(self) -> SaveFileConverter:
        """Create a converter instance."""
        with patch("shutil.which", return_value="/usr/bin/uesave"):
            return SaveFileConverter()

    def test_parse_empty_stockpile(self, converter: SaveFileConverter) -> None:
        """Test parsing empty stockpile info."""
        result = converter._parse_stockpile_items({})
        assert result == []

    def test_parse_items(self, converter: SaveFileConverter) -> None:
        """Test parsing non-crated items."""
        stockpile_info: dict[str, Any] = {
            "Items_0": [
                {"CodeName_0": "Rifle", "Quantity_0": 100},
                {"CodeName_0": "Ammo", "Quantity_0": 500},
            ]
        }
        result = converter._parse_stockpile_items(stockpile_info)

        assert len(result) == 2
        # Should be sorted by quantity descending
        assert result[0].code == "Ammo"
        assert result[0].quantity == 500
        assert result[0].crated is False
        assert result[0].confidence is None  # Save file data is exact

        assert result[1].code == "Rifle"
        assert result[1].quantity == 100

    def test_parse_crated_items(self, converter: SaveFileConverter) -> None:
        """Test parsing crated items."""
        stockpile_info: dict[str, Any] = {
            "ItemCrates_0": [
                {"CodeName_0": "RifleCrate", "Quantity_0": 10},
            ]
        }
        result = converter._parse_stockpile_items(stockpile_info)

        assert len(result) == 1
        assert result[0].crated is True

    def test_parse_vehicles(self, converter: SaveFileConverter) -> None:
        """Test parsing vehicles (crated and non-crated)."""
        stockpile_info: dict[str, Any] = {
            "Vehicles_0": [{"CodeName_0": "Truck", "Quantity_0": 5}],
            "VehicleCrates_0": [{"CodeName_0": "TankCrate", "Quantity_0": 2}],
        }
        result = converter._parse_stockpile_items(stockpile_info)

        assert len(result) == 2
        # Non-crated first, then crated
        assert result[0].code == "Truck"
        assert result[0].crated is False
        assert result[1].code == "TankCrate"
        assert result[1].crated is True

    def test_parse_structures(self, converter: SaveFileConverter) -> None:
        """Test parsing structures."""
        stockpile_info: dict[str, Any] = {
            "Structures_0": [{"CodeName_0": "Bunker", "Quantity_0": 3}],
            "StructureCrates_0": [{"CodeName_0": "WallCrate", "Quantity_0": 1}],
        }
        result = converter._parse_stockpile_items(stockpile_info)

        assert len(result) == 2

    def test_parse_all_categories_ordering(self, converter: SaveFileConverter) -> None:
        """Test that all categories are in correct order."""
        stockpile_info: dict[str, Any] = {
            "Items_0": [{"CodeName_0": "Item1", "Quantity_0": 1}],
            "ItemCrates_0": [{"CodeName_0": "Item2", "Quantity_0": 1}],
            "Vehicles_0": [{"CodeName_0": "Item3", "Quantity_0": 1}],
            "VehicleCrates_0": [{"CodeName_0": "Item4", "Quantity_0": 1}],
            "Structures_0": [{"CodeName_0": "Item5", "Quantity_0": 1}],
            "StructureCrates_0": [{"CodeName_0": "Item6", "Quantity_0": 1}],
        }
        result = converter._parse_stockpile_items(stockpile_info)

        assert len(result) == 6
        # Order: Items, ItemCrates, Vehicles, VehicleCrates, Structures, StructureCrates
        assert result[0].code == "Item1"
        assert result[1].code == "Item2"
        assert result[2].code == "Item3"
        assert result[3].code == "Item4"
        assert result[4].code == "Item5"
        assert result[5].code == "Item6"


class TestParseTooltip:
    """Test suite for parsing tooltips."""

    @pytest.fixture
    def converter(self) -> SaveFileConverter:
        """Create a converter instance."""
        with patch("shutil.which", return_value="/usr/bin/uesave"):
            return SaveFileConverter()

    def test_parse_basic_tooltip(self, converter: SaveFileConverter) -> None:
        """Test parsing a basic tooltip."""
        tooltip: dict[str, Any] = {
            "CodeName_0": "Seaport",
            "MapId_0": "EWorldConquestMapId::TerminusHex",
            "NormalizedMapCoords_0": {"x": 0.5, "y": 0.6},
            "LastUpdated_0": 0,
            "RecentMapItemDetails_0": {
                "StockpileInfo_0": {"Items_0": [{"CodeName_0": "Rifle", "Quantity_0": 50}]}
            },
        }
        result = converter._parse_tooltip(tooltip)

        assert len(result) == 1
        stockpile = result[0]
        assert stockpile.name == ""  # Public stockpiles have empty name
        assert stockpile.type == StockpileType.SEAPORT
        assert stockpile.hex == "TerminusHex"
        assert stockpile.coords is not None
        assert stockpile.coords.x == 0.5
        assert stockpile.coords.y == 0.6
        assert stockpile.is_reserve is False
        assert len(stockpile.items) == 1

    def test_parse_tooltip_with_reserves(self, converter: SaveFileConverter) -> None:
        """Test parsing tooltip with reserve stockpiles."""
        tooltip: dict[str, Any] = {
            "CodeName_0": "StorageFacility",
            "MapId_0": "TestHex",
            "NormalizedMapCoords_0": {"x": 0.1, "y": 0.2},
            "LastUpdated_0": 0,
            "RecentMapItemDetails_0": {
                "StockpileInfo_0": {},
                "ReserveStockpileInfoList_0": [
                    {
                        "StockpileName_0": "Logi Reserve",
                        "StockpileInfo_0": {
                            "Items_0": [{"CodeName_0": "Bmats", "Quantity_0": 1000}]
                        },
                    },
                    {
                        "StockpileName_0": "Tank Reserve",
                        "StockpileInfo_0": {},
                    },
                ],
            },
        }
        result = converter._parse_tooltip(tooltip)

        assert len(result) == 3  # Main + 2 reserves

        # Main stockpile
        assert result[0].name == ""  # Public stockpiles have empty name
        assert result[0].is_reserve is False

        # First reserve
        assert result[1].name == "Logi Reserve"
        assert result[1].is_reserve is True
        assert len(result[1].items) == 1

        # Second reserve
        assert result[2].name == "Tank Reserve"
        assert result[2].is_reserve is True

    def test_parse_tooltip_unknown_type(self, converter: SaveFileConverter) -> None:
        """Test parsing tooltip with unknown stockpile type."""
        tooltip: dict[str, Any] = {
            "CodeName_0": "UnknownType",
            "MapId_0": "TestHex",
            "NormalizedMapCoords_0": {"x": 0.0, "y": 0.0},
            "LastUpdated_0": 0,
            "RecentMapItemDetails_0": {"StockpileInfo_0": {}},
        }
        result = converter._parse_tooltip(tooltip)

        assert len(result) == 1
        assert result[0].type == StockpileType.UNDEFINED


class TestParseStockpiles:
    """Test suite for parsing full stockpiles from save data."""

    @pytest.fixture
    def converter(self) -> SaveFileConverter:
        """Create a converter instance."""
        with patch("shutil.which", return_value="/usr/bin/uesave"):
            return SaveFileConverter()

    def test_parse_empty_save_data(self, converter: SaveFileConverter) -> None:
        """Test parsing empty save data."""
        result = converter.parse_stockpiles({})
        assert result == []

    def test_parse_save_data_no_tooltips(self, converter: SaveFileConverter) -> None:
        """Test parsing save data with no tooltips."""
        save_data: dict[str, Any] = {"root": {"properties": {}}}
        result = converter.parse_stockpiles(save_data)
        assert result == []

    def test_parse_save_data_with_tooltips(self, converter: SaveFileConverter) -> None:
        """Test parsing save data with tooltips."""
        save_data: dict[str, Any] = {
            "root": {
                "properties": {
                    "PinnedMapToolTipsC_0": [
                        {
                            "CodeName_0": "Seaport",
                            "MapId_0": "Hex1",
                            "NormalizedMapCoords_0": {"x": 0.5, "y": 0.5},
                            "LastUpdated_0": 0,
                            "RecentMapItemDetails_0": {"StockpileInfo_0": {}},
                        },
                        {
                            "CodeName_0": "StorageFacility",
                            "MapId_0": "Hex2",
                            "NormalizedMapCoords_0": {"x": 0.1, "y": 0.1},
                            "LastUpdated_0": 0,
                            "RecentMapItemDetails_0": {"StockpileInfo_0": {}},
                        },
                    ]
                }
            }
        }
        result = converter.parse_stockpiles(save_data)

        assert len(result) == 2
        assert result[0].hex == "Hex1"
        assert result[1].hex == "Hex2"


class TestConvertSavToJson:
    """Test suite for convert_sav_to_json method."""

    @pytest.fixture
    def converter(self) -> SaveFileConverter:
        """Create a converter instance."""
        with patch("shutil.which", return_value="/usr/bin/uesave"):
            return SaveFileConverter()

    def test_convert_sav_success(self, converter: SaveFileConverter, tmp_path: Path) -> None:
        """Test successful conversion."""
        sav_file = tmp_path / "test.sav"
        sav_file.touch()

        expected_json: dict[str, Any] = {"root": {"properties": {}}}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Mock the temp file to contain valid JSON
            with patch("builtins.open", MagicMock()) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
                    expected_json
                )

                with patch("json.load", return_value=expected_json):
                    result = converter.convert_sav_to_json(sav_file)
                    assert result == expected_json

    def test_convert_sav_command_failure(
        self, converter: SaveFileConverter, tmp_path: Path
    ) -> None:
        """Test handling of subprocess failure."""
        import subprocess

        sav_file = tmp_path / "test.sav"
        sav_file.touch()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "uesave")

            with pytest.raises(subprocess.CalledProcessError):
                converter.convert_sav_to_json(sav_file)


class TestConvertFile:
    """Test suite for convert_file method."""

    @pytest.fixture
    def converter(self) -> SaveFileConverter:
        """Create a converter instance."""
        with patch("shutil.which", return_value="/usr/bin/uesave"):
            return SaveFileConverter()

    def test_convert_file_integration(self, converter: SaveFileConverter, tmp_path: Path) -> None:
        """Test convert_file calls both methods correctly."""
        sav_file = tmp_path / "test.sav"
        sav_file.touch()

        mock_json: dict[str, Any] = {
            "root": {
                "properties": {
                    "PinnedMapToolTipsC_0": [
                        {
                            "CodeName_0": "Seaport",
                            "MapId_0": "TestHex",
                            "NormalizedMapCoords_0": {"x": 0.5, "y": 0.5},
                            "LastUpdated_0": 0,
                            "RecentMapItemDetails_0": {"StockpileInfo_0": {}},
                        }
                    ]
                }
            }
        }

        with patch.object(converter, "convert_sav_to_json", return_value=mock_json) as mock_convert:
            result = converter.convert_file(sav_file)

            mock_convert.assert_called_once_with(sav_file)
            assert len(result) == 1
            assert result[0].type == StockpileType.SEAPORT
