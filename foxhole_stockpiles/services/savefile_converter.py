"""Service to convert Foxhole save file JSON to Stockpile format."""

import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_coords import StockpileCoords
from foxhole_stockpiles.models.stockpile_item import StockpileItem


class SaveFileConverter:
    """Converts Foxhole save files to Stockpile format."""

    def __init__(self, uesave_path: Path | None = None) -> None:
        """Initialize the converter.

        Args:
            uesave_path (Path | None): Path to uesave binary. If None, searches PATH.

        Raises:
            FileNotFoundError: If uesave is not found.
        """
        if uesave_path is not None:
            self._uesave_path = uesave_path
        else:
            found = shutil.which("uesave")
            if found is None:
                raise FileNotFoundError(
                    "uesave not found. Install with: "
                    "cargo install --git https://github.com/trumank/uesave.git"
                )
            self._uesave_path = Path(found)

    def convert_sav_to_json(self, sav_path: Path) -> dict[str, Any]:
        """Convert a .sav file to JSON using uesave.

        Args:
            sav_path (Path): Path to the .sav file.

        Returns:
            dict[str, Any]: Parsed JSON data.

        Raises:
            subprocess.CalledProcessError: If uesave fails.
            json.JSONDecodeError: If output is not valid JSON.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_json = Path(f.name)

        try:
            subprocess.run(
                [
                    str(self._uesave_path),
                    "to-json",
                    "-i",
                    str(sav_path),
                    "-o",
                    str(temp_json),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            with open(temp_json, encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        finally:
            temp_json.unlink(missing_ok=True)

    def parse_stockpiles(self, save_data: dict[str, Any]) -> list[Stockpile]:
        """Parse stockpiles from save file JSON.

        Args:
            save_data (dict[str, Any]): Parsed save file JSON.

        Returns:
            list[Stockpile]: List of parsed stockpiles.
        """
        stockpiles: list[Stockpile] = []

        # Navigate to PinnedMapToolTipsC_0
        properties = save_data.get("root", {}).get("properties", {})
        pinned_tooltips = properties.get("PinnedMapToolTipsC_0", [])

        for tooltip in pinned_tooltips:
            # _parse_tooltip returns a list (main + reserves)
            parsed_list = self._parse_tooltip(tooltip)
            stockpiles.extend(parsed_list)

        return stockpiles

    def _parse_tooltip(self, tooltip: dict[str, Any]) -> list[Stockpile]:
        """Parse a single tooltip into Stockpiles (main + reserves).

        Args:
            tooltip (dict[str, Any]): Tooltip data from save file.

        Returns:
            list[Stockpile]: List of stockpiles (main + any reserves).
        """
        result: list[Stockpile] = []

        code_name = tooltip.get("CodeName_0", "")
        try:
            stockpile_type = StockpileType(code_name)
        except ValueError:
            stockpile_type = StockpileType.UNDEFINED

        # Extract map/region info (hex)
        map_id = tooltip.get("MapId_0", "")
        # Clean up map ID (e.g., "EWorldConquestMapId::TerminusHex" -> "TerminusHex")
        if "::" in map_id:
            map_id = map_id.split("::")[-1]

        # Extract coordinates
        coords_data = tooltip.get("NormalizedMapCoords_0", {})
        coords = StockpileCoords(
            x=coords_data.get("x", 0.0),
            y=coords_data.get("y", 0.0),
        )

        # Get raw timestamp for tracking
        raw_timestamp = tooltip.get("LastUpdated_0", 0)
        updated_at = self._parse_ue_timestamp(raw_timestamp)

        # Get stockpile info from RecentMapItemDetails_0 (most recent data)
        details = tooltip.get("RecentMapItemDetails_0", {})
        stockpile_data = details.get("StockpileInfo_0", {})

        # Parse main stockpile items
        items = self._parse_stockpile_items(stockpile_data)

        # Main stockpile (public) - name is empty for public stockpiles
        result.append(
            Stockpile(
                name="",
                type=stockpile_type,
                items=items,
                timestamp=updated_at,
                coords=coords,
                hex=map_id,
                is_reserve=False,
                raw_timestamp=raw_timestamp,
            )
        )

        # Parse reserve stockpiles (named private stockpiles)
        reserve_list = details.get("ReserveStockpileInfoList_0", [])
        for reserve in reserve_list:
            reserve_name = reserve.get("StockpileName_0", "")
            reserve_data = reserve.get("StockpileInfo_0", {})
            reserve_items = self._parse_stockpile_items(reserve_data)

            result.append(
                Stockpile(
                    name=reserve_name,
                    type=stockpile_type,
                    items=reserve_items,
                    timestamp=updated_at,
                    coords=coords,
                    hex=map_id,
                    is_reserve=True,
                    raw_timestamp=raw_timestamp,
                )
            )

        return result

    def _parse_stockpile_items(self, stockpile_info: dict[str, Any]) -> list[StockpileItem]:
        """Parse stockpile info into list of StockpileItems.

        Items are grouped by category and sorted by quantity (descending) within each group.
        Order: Items, ItemCrates, Vehicles, VehicleCrates, Structures, StructureCrates.

        Args:
            stockpile_info (dict[str, Any]): StockpileInfo_0 data.

        Returns:
            list[StockpileItem]: List of parsed items.
        """
        items: list[StockpileItem] = []

        # Non-crated items (sorted by quantity descending)
        group = [
            StockpileItem(
                code=item.get("CodeName_0", "Unknown"),
                quantity=item.get("Quantity_0", 0),
                crated=False,
                confidence=None,  # Save file data is exact, no confidence needed
            )
            for item in stockpile_info.get("Items_0", [])
        ]
        items.extend(sorted(group, key=lambda x: x.quantity, reverse=True))

        # Crated items (sorted by quantity descending)
        group = [
            StockpileItem(
                code=item.get("CodeName_0", "Unknown"),
                quantity=item.get("Quantity_0", 0),
                crated=True,
                confidence=None,
            )
            for item in stockpile_info.get("ItemCrates_0", [])
        ]
        items.extend(sorted(group, key=lambda x: x.quantity, reverse=True))

        # Vehicles non-crated (sorted by quantity descending)
        group = [
            StockpileItem(
                code=item.get("CodeName_0", "Unknown"),
                quantity=item.get("Quantity_0", 0),
                crated=False,
                confidence=None,
            )
            for item in stockpile_info.get("Vehicles_0", [])
        ]
        items.extend(sorted(group, key=lambda x: x.quantity, reverse=True))

        # Vehicle crates (sorted by quantity descending)
        group = [
            StockpileItem(
                code=item.get("CodeName_0", "Unknown"),
                quantity=item.get("Quantity_0", 0),
                crated=True,
                confidence=None,
            )
            for item in stockpile_info.get("VehicleCrates_0", [])
        ]
        items.extend(sorted(group, key=lambda x: x.quantity, reverse=True))

        # Structures non-crated (sorted by quantity descending)
        group = [
            StockpileItem(
                code=item.get("CodeName_0", "Unknown"),
                quantity=item.get("Quantity_0", 0),
                crated=False,
                confidence=None,
            )
            for item in stockpile_info.get("Structures_0", [])
        ]
        items.extend(sorted(group, key=lambda x: x.quantity, reverse=True))

        # Structure crates (sorted by quantity descending)
        group = [
            StockpileItem(
                code=item.get("CodeName_0", "Unknown"),
                quantity=item.get("Quantity_0", 0),
                crated=True,
                confidence=None,
            )
            for item in stockpile_info.get("StructureCrates_0", [])
        ]
        items.extend(sorted(group, key=lambda x: x.quantity, reverse=True))

        return items

    def _parse_ue_timestamp(self, ticks: int) -> datetime:
        """Convert Unreal Engine ticks to datetime.

        Args:
            ticks (int): Unreal Engine timestamp ticks.

        Returns:
            datetime: Parsed datetime.
        """
        if ticks == 0:
            return datetime.now(tz=UTC)

        try:
            # UE ticks are 100-nanosecond intervals since 0001-01-01
            # Convert to Unix timestamp
            epoch_ticks = 621355968000000000  # Ticks from 0001-01-01 to 1970-01-01
            unix_ticks = ticks - epoch_ticks
            unix_seconds = unix_ticks / 10_000_000
            return datetime.fromtimestamp(unix_seconds, tz=UTC)
        except (ValueError, OSError, OverflowError):
            return datetime.now(tz=UTC)

    def convert_file(self, sav_path: Path) -> list[Stockpile]:
        """Convert a save file to list of Stockpiles.

        Args:
            sav_path (Path): Path to the .sav file.

        Returns:
            list[Stockpile]: List of parsed stockpiles.
        """
        save_data = self.convert_sav_to_json(sav_path)
        return self.parse_stockpiles(save_data)
