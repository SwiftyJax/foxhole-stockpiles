"""Tests for commands.process_sav module."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from foxhole_stockpiles.commands.process_sav.process_sav import (
    _find_mapdata_file,
    _get_default_savefile_path,
    main,
)
from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_coords import StockpileCoords
from foxhole_stockpiles.services.savefile_processor import SaveFileProcessor


class TestGetDefaultSavefilePath:
    """Test suite for _get_default_savefile_path function."""

    def test_windows_path(self) -> None:
        """Test Windows path detection."""
        with patch("sys.platform", "win32"):
            with patch.dict("os.environ", {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}):
                result = _get_default_savefile_path()
                assert result is not None
                assert "Foxhole" in str(result)
                assert "SaveGames" in str(result)

    def test_windows_no_localappdata(self) -> None:
        """Test Windows with no LOCALAPPDATA returns None."""
        with patch("sys.platform", "win32"):
            with patch.dict("os.environ", {}, clear=True):
                result = _get_default_savefile_path()
                assert result is None

    def test_unsupported_platform(self) -> None:
        """Test unsupported platform returns None."""
        with patch("sys.platform", "darwin"):
            result = _get_default_savefile_path()
            assert result is None

    def test_linux_no_wsl_no_proton(self, tmp_path: Path) -> None:
        """Test Linux when neither WSL nor Proton paths exist."""
        # Create mock for Path("/mnt/c/Users") that doesn't exist
        original_path_class = Path

        def mock_path_init(path_str: str) -> Path:
            if path_str == "/mnt/c/Users":
                # Return a path in tmp_path that doesn't exist
                return tmp_path / "fake_mnt_c_Users"
            return original_path_class(path_str)

        with patch("sys.platform", "linux"):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.Path",
                side_effect=mock_path_init,
            ) as mock_path:
                mock_path.home = MagicMock(return_value=tmp_path)
                result = _get_default_savefile_path()
                # Should return None since no paths exist
                assert result is None

    def test_linux_proton_path_found(self, tmp_path: Path) -> None:
        """Test Linux Proton/Wine path detection."""
        # Create Proton-like structure
        proton_path = (
            tmp_path
            / ".steam"
            / "steam"
            / "steamapps"
            / "compatdata"
            / "505460"
            / "pfx"
            / "drive_c"
            / "users"
            / "steamuser"
            / "AppData"
            / "Local"
            / "Foxhole"
            / "Saved"
            / "SaveGames"
        )
        proton_path.mkdir(parents=True)

        original_path_class = Path

        def mock_path_init(path_str: str) -> Path:
            if path_str == "/mnt/c/Users":
                # Return a path that doesn't exist
                return tmp_path / "fake_mnt_c_Users"
            return original_path_class(path_str)

        with patch("sys.platform", "linux"):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.Path",
                side_effect=mock_path_init,
            ) as mock_path:
                mock_path.home = MagicMock(return_value=tmp_path)
                result = _get_default_savefile_path()
                assert result == proton_path

    def test_linux_wsl_iterdir_permission_error(self, tmp_path: Path) -> None:
        """Test WSL path handles PermissionError on iterdir."""
        # Mock a WSL users directory that exists but raises PermissionError on iterdir
        mock_wsl_users = MagicMock()
        mock_wsl_users.exists.return_value = True
        mock_wsl_users.iterdir.side_effect = PermissionError("Access denied")

        original_path_class = Path

        def mock_path_init(path_str: str) -> Any:
            if path_str == "/mnt/c/Users":
                return mock_wsl_users
            return original_path_class(path_str)

        with patch("sys.platform", "linux"):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.Path",
                side_effect=mock_path_init,
            ) as mock_path:
                mock_path.home = MagicMock(return_value=tmp_path)
                result = _get_default_savefile_path()
                # Should return None since no valid path found
                assert result is None

    def test_linux_wsl_user_dir_permission_error(self, tmp_path: Path) -> None:
        """Test WSL path handles PermissionError when accessing user directories."""
        # Create a mock user directory that raises PermissionError on path operations
        mock_user_dir = MagicMock()
        mock_user_dir.__truediv__ = MagicMock(side_effect=PermissionError("No access"))

        mock_wsl_users = MagicMock()
        mock_wsl_users.exists.return_value = True
        mock_wsl_users.iterdir.return_value = [mock_user_dir]

        original_path_class = Path

        def mock_path_init(path_str: str) -> Any:
            if path_str == "/mnt/c/Users":
                return mock_wsl_users
            return original_path_class(path_str)

        with patch("sys.platform", "linux"):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.Path",
                side_effect=mock_path_init,
            ) as mock_path:
                mock_path.home = MagicMock(return_value=tmp_path)
                result = _get_default_savefile_path()
                # Should return None since permission errors are caught
                assert result is None

    def test_linux_wsl_path_found(self, tmp_path: Path) -> None:
        """Test WSL path detection when save directory exists."""
        # Create WSL-like structure
        wsl_users = tmp_path / "wsl_users"
        user_dir = wsl_users / "TestUser"
        save_path = user_dir / "AppData" / "Local" / "Foxhole" / "Saved" / "SaveGames"
        save_path.mkdir(parents=True)

        original_path_class = Path

        def mock_path_init(path_str: str) -> Path:
            if path_str == "/mnt/c/Users":
                return wsl_users
            return original_path_class(path_str)

        with patch("sys.platform", "linux"):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.Path",
                side_effect=mock_path_init,
            ) as mock_path:
                mock_path.home = MagicMock(return_value=tmp_path)
                result = _get_default_savefile_path()
                # Should return the save path
                assert result == save_path


class TestFindMapdataFile:
    """Test suite for _find_mapdata_file function."""

    def test_find_existing_file(self, tmp_path: Path) -> None:
        """Test finding existing MapData.sav file."""
        mapdata = tmp_path / "12345_MapData.sav"
        mapdata.touch()

        result = _find_mapdata_file(tmp_path)
        assert result == mapdata

    def test_no_mapdata_file(self, tmp_path: Path) -> None:
        """Test when no MapData.sav exists."""
        result = _find_mapdata_file(tmp_path)
        assert result is None

    def test_finds_first_matching_file(self, tmp_path: Path) -> None:
        """Test finds first match when multiple exist."""
        (tmp_path / "111_MapData.sav").touch()
        (tmp_path / "222_MapData.sav").touch()

        result = _find_mapdata_file(tmp_path)
        assert result is not None
        assert "_MapData.sav" in str(result)


class TestSaveFileProcessorInit:
    """Test suite for SaveFileProcessor initialization."""

    def test_init_with_defaults(self, tmp_path: Path) -> None:
        """Test initialization with default values."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

        assert monitor._poll_interval == 1.0
        assert monitor._emit_all_on_start is False
        assert monitor._running is False
        assert monitor._stockpile_cache == {}

    def test_init_with_custom_values(self, tmp_path: Path) -> None:
        """Test initialization with custom values."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=5.0,
            emit_all_on_start=False,
        )

        assert monitor._poll_interval == 5.0
        assert monitor._emit_all_on_start is False


class TestSaveFileProcessorProperties:
    """Test suite for SaveFileProcessor properties."""

    def test_file_path_property(self, tmp_path: Path) -> None:
        """Test file_path property."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()
        expected_path = tmp_path / "test.sav"

        monitor = SaveFileProcessor(
            file_path=expected_path,
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

        assert monitor.file_path == expected_path

    def test_poll_interval_property_getter(self, tmp_path: Path) -> None:
        """Test poll_interval property getter."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=2.5,
        )

        assert monitor.poll_interval == 2.5

    def test_poll_interval_property_setter(self, tmp_path: Path) -> None:
        """Test poll_interval property setter."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=1.0,
        )

        monitor.poll_interval = 5.0
        assert monitor.poll_interval == 5.0

    def test_is_running_property(self, tmp_path: Path) -> None:
        """Test is_running property."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

        assert monitor.is_running is False
        monitor._running = True
        assert monitor.is_running is True


class TestSaveFileProcessorDetectChanges:
    """Test suite for SaveFileProcessor._detect_changes method."""

    @pytest.fixture
    def monitor(self, tmp_path: Path) -> SaveFileProcessor:
        """Create a monitor instance."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()
        return SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

    def _create_stockpile(
        self,
        name: str = "Test",
        stockpile_type: StockpileType = StockpileType.SEAPORT,
        raw_timestamp: int | None = 100,
        coords_x: float = 0.5,
        coords_y: float = 0.5,
        hex_name: str = "TestHex",
        is_reserve: bool = False,
    ) -> Stockpile:
        """Create a test stockpile."""
        return Stockpile(
            name=name,
            type=stockpile_type,
            items=[],
            timestamp=datetime.now(tz=UTC),
            coords=StockpileCoords(x=coords_x, y=coords_y),
            hex=hex_name,
            is_reserve=is_reserve,
            raw_timestamp=raw_timestamp,
        )

    def test_detect_new_stockpile(self, monitor: SaveFileProcessor) -> None:
        """Test detecting new stockpiles."""
        stockpiles = [self._create_stockpile(name="New", raw_timestamp=100)]

        updated, new, removed = monitor._detect_changes(stockpiles)

        assert len(new) == 1
        assert new[0].name == "New"
        assert len(updated) == 0
        assert len(removed) == 0
        # Check cache was populated
        assert len(monitor._stockpile_cache) == 1

    def test_detect_updated_stockpile(self, monitor: SaveFileProcessor) -> None:
        """Test detecting updated stockpiles."""
        stockpile = self._create_stockpile(name="Existing", raw_timestamp=100)
        # Pre-populate cache
        monitor._stockpile_cache[stockpile.to_key()] = 100

        # Update with new timestamp
        updated_stockpile = self._create_stockpile(name="Existing", raw_timestamp=200)
        updated, new, removed = monitor._detect_changes([updated_stockpile])

        assert len(updated) == 1
        assert len(new) == 0
        assert len(removed) == 0
        # Check cache was updated
        assert monitor._stockpile_cache[stockpile.to_key()] == 200

    def test_detect_unchanged_stockpile(self, monitor: SaveFileProcessor) -> None:
        """Test detecting unchanged stockpiles."""
        stockpile = self._create_stockpile(name="Unchanged", raw_timestamp=100)
        # Pre-populate cache with same timestamp
        monitor._stockpile_cache[stockpile.to_key()] = 100

        updated, new, removed = monitor._detect_changes([stockpile])

        assert len(updated) == 0
        assert len(new) == 0
        assert len(removed) == 0

    def test_detect_removed_stockpile(self, monitor: SaveFileProcessor) -> None:
        """Test detecting removed stockpiles."""
        # Pre-populate cache
        monitor._stockpile_cache["seaport:TestHex:0.500_0.500:public"] = 100

        # Empty list means stockpile was removed
        updated, new, removed = monitor._detect_changes([])

        assert len(updated) == 0
        assert len(new) == 0
        assert len(removed) == 1
        assert "seaport:TestHex:0.500_0.500:public" in removed
        # Check cache was cleaned
        assert len(monitor._stockpile_cache) == 0

    def test_detect_mixed_changes(self, monitor: SaveFileProcessor) -> None:
        """Test detecting mixed changes."""
        # Pre-populate cache
        existing = self._create_stockpile(
            name="Existing", raw_timestamp=100, coords_x=0.1, coords_y=0.1
        )
        monitor._stockpile_cache[existing.to_key()] = 100

        to_remove_key = "seaport:TestHex:0.999_0.999:public"
        monitor._stockpile_cache[to_remove_key] = 50

        # Create changes
        updated_existing = self._create_stockpile(
            name="Existing", raw_timestamp=200, coords_x=0.1, coords_y=0.1
        )
        new_stockpile = self._create_stockpile(
            name="NewOne", raw_timestamp=300, coords_x=0.2, coords_y=0.2
        )

        updated, new, removed = monitor._detect_changes([updated_existing, new_stockpile])

        assert len(updated) == 1
        assert len(new) == 1
        assert len(removed) == 1


class TestSaveFileProcessorOutputResults:
    """Test suite for SaveFileProcessor._output_results method."""

    @pytest.fixture
    def monitor(self, tmp_path: Path) -> SaveFileProcessor:
        """Create a monitor instance with mock coordinator."""
        mock_converter = MagicMock()
        mock_coordinator = AsyncMock()
        return SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

    @pytest.mark.asyncio
    async def test_output_empty_list(self, monitor: SaveFileProcessor) -> None:
        """Test outputting empty list does nothing."""
        await monitor._output_results([])

        monitor._output_coordinator.handle_output.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_output_stockpiles(self, monitor: SaveFileProcessor) -> None:
        """Test outputting stockpiles calls handler."""
        stockpiles = [
            Stockpile(
                name="Test",
                type=StockpileType.SEAPORT,
                items=[],
                timestamp=datetime.now(tz=UTC),
            )
        ]

        await monitor._output_results(stockpiles)

        monitor._output_coordinator.handle_output.assert_called_once_with(stockpiles)  # type: ignore[attr-defined]


class TestSaveFileProcessorRunOnce:
    """Test suite for SaveFileProcessor.run_once method."""

    @pytest.fixture
    def mock_stockpiles(self) -> list[Stockpile]:
        """Create mock stockpiles."""
        return [
            Stockpile(
                name="Test",
                type=StockpileType.SEAPORT,
                items=[],
                timestamp=datetime.now(tz=UTC),
                raw_timestamp=100,
            )
        ]

    @pytest.mark.asyncio
    async def test_run_once_emits_all(
        self, tmp_path: Path, mock_stockpiles: list[Stockpile]
    ) -> None:
        """Test run_once emits all stockpiles."""
        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = mock_stockpiles
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            emit_all_on_start=True,
        )

        await monitor.run_once()

        mock_coordinator.handle_output.assert_called_once_with(mock_stockpiles)


class TestSaveFileProcessorStop:
    """Test suite for SaveFileProcessor.stop method."""

    def test_stop_sets_flag(self, tmp_path: Path) -> None:
        """Test stop sets running flag to False."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )
        monitor._running = True

        monitor.stop()

        assert monitor._running is False


class TestSaveFileProcessorClearCache:
    """Test suite for SaveFileProcessor.clear_cache method."""

    def test_clear_cache_empties_stockpile_cache(self, tmp_path: Path) -> None:
        """Test clear_cache empties the stockpile cache."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )
        monitor._stockpile_cache["key1"] = 100
        monitor._stockpile_cache["key2"] = 200

        monitor.clear_cache()

        assert monitor._stockpile_cache == {}

    def test_clear_cache_resets_last_mtime(self, tmp_path: Path) -> None:
        """Test clear_cache resets last_mtime."""
        mock_converter = MagicMock()
        mock_coordinator = MagicMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )
        monitor._last_mtime = 12345.0

        monitor.clear_cache()

        assert monitor._last_mtime is None


class TestSaveFileProcessorProcessFile:
    """Test suite for SaveFileProcessor._process_file method."""

    @pytest.fixture
    def mock_stockpiles(self) -> list[Stockpile]:
        """Create mock stockpiles."""
        return [
            Stockpile(
                name="Seaport1",
                type=StockpileType.SEAPORT,
                items=[],
                timestamp=datetime.now(tz=UTC),
                coords=StockpileCoords(x=0.5, y=0.5),
                hex="TestHex",
                raw_timestamp=100,
            )
        ]

    @pytest.mark.asyncio
    async def test_process_file_initial_load(
        self, tmp_path: Path, mock_stockpiles: list[Stockpile]
    ) -> None:
        """Test initial load emits all stockpiles when emit_all_on_start=True."""
        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = mock_stockpiles
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            emit_all_on_start=True,
        )

        await monitor._process_file(is_initial=True)

        mock_coordinator.handle_output.assert_called_once_with(mock_stockpiles)
        # Cache should be populated
        assert len(monitor._stockpile_cache) == 1

    @pytest.mark.asyncio
    async def test_process_file_no_changes(
        self, tmp_path: Path, mock_stockpiles: list[Stockpile]
    ) -> None:
        """Test subsequent load with no changes doesn't emit."""
        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = mock_stockpiles
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

        # Pre-populate cache
        monitor._stockpile_cache[mock_stockpiles[0].to_key()] = 100

        await monitor._process_file(is_initial=False)

        # Should not emit since no changes
        mock_coordinator.handle_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_handles_error(self, tmp_path: Path) -> None:
        """Test process_file handles converter errors gracefully."""
        mock_converter = MagicMock()
        mock_converter.convert_file.side_effect = Exception("Conversion failed")
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

        # Should not raise
        await monitor._process_file(is_initial=True)

        mock_coordinator.handle_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_empty_stockpiles(self, tmp_path: Path) -> None:
        """Test process_file handles empty stockpile list."""
        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = []
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

        await monitor._process_file(is_initial=True)

        mock_coordinator.handle_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_with_new_stockpiles(self, tmp_path: Path) -> None:
        """Test process_file detects and outputs new stockpiles."""
        new_stockpile = Stockpile(
            name="NewStockpile",
            type=StockpileType.SEAPORT,
            items=[],
            timestamp=datetime.now(tz=UTC),
            coords=StockpileCoords(x=0.1, y=0.1),
            hex="TestHex",
            raw_timestamp=200,
        )
        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = [new_stockpile]
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )

        result = await monitor._process_file(is_initial=False)

        assert len(result) == 1
        assert result[0].name == "NewStockpile"
        mock_coordinator.handle_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_with_updated_stockpiles(self, tmp_path: Path) -> None:
        """Test process_file detects and outputs updated stockpiles."""
        stockpile = Stockpile(
            name="UpdatedStockpile",
            type=StockpileType.SEAPORT,
            items=[],
            timestamp=datetime.now(tz=UTC),
            coords=StockpileCoords(x=0.2, y=0.2),
            hex="TestHex",
            raw_timestamp=300,  # New timestamp
        )
        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = [stockpile]
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )
        # Pre-populate cache with old timestamp
        monitor._stockpile_cache[stockpile.to_key()] = 100

        result = await monitor._process_file(is_initial=False)

        assert len(result) == 1
        assert result[0].name == "UpdatedStockpile"
        mock_coordinator.handle_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_with_removed_stockpiles(self, tmp_path: Path) -> None:
        """Test process_file detects removed stockpiles when some remain."""
        # Create a remaining stockpile
        remaining = Stockpile(
            name="Remaining",
            type=StockpileType.STORAGE_DEPOT,
            items=[],
            timestamp=datetime.now(tz=UTC),
            coords=StockpileCoords(x=0.1, y=0.1),
            hex="TestHex",
            raw_timestamp=200,
        )

        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = [remaining]  # Only one remains
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )
        # Pre-populate cache with two stockpiles
        monitor._stockpile_cache[remaining.to_key()] = 200  # Same timestamp - no update
        monitor._stockpile_cache["seaport:TestHex:0.500_0.500:public"] = 100  # Will be removed

        result = await monitor._process_file(is_initial=False)

        # No new/updated stockpiles to output (remaining has same timestamp)
        assert len(result) == 0
        # Removed stockpile should be gone from cache
        assert "seaport:TestHex:0.500_0.500:public" not in monitor._stockpile_cache
        # Remaining should still be in cache
        assert remaining.to_key() in monitor._stockpile_cache

    @pytest.mark.asyncio
    async def test_process_file_with_mixed_changes(self, tmp_path: Path) -> None:
        """Test process_file with new, updated, and removed stockpiles."""
        new_stockpile = Stockpile(
            name="New",
            type=StockpileType.SEAPORT,
            items=[],
            timestamp=datetime.now(tz=UTC),
            coords=StockpileCoords(x=0.1, y=0.1),
            hex="TestHex",
            raw_timestamp=100,
        )
        updated_stockpile = Stockpile(
            name="Updated",
            type=StockpileType.STORAGE_DEPOT,
            items=[],
            timestamp=datetime.now(tz=UTC),
            coords=StockpileCoords(x=0.2, y=0.2),
            hex="TestHex",
            raw_timestamp=200,
        )

        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = [new_stockpile, updated_stockpile]
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=tmp_path / "test.sav",
            converter=mock_converter,
            output_coordinator=mock_coordinator,
        )
        # Pre-populate cache with old timestamp for updated stockpile and a removed one
        monitor._stockpile_cache[updated_stockpile.to_key()] = 50  # Old timestamp
        monitor._stockpile_cache["seaport:OtherHex:0.9_0.9:public"] = 999  # Will be removed

        result = await monitor._process_file(is_initial=False)

        # Should have new + updated
        assert len(result) == 2
        # Each stockpile has different coords, so 2 location groups = 2 handler calls
        assert mock_coordinator.handle_output.call_count == 2
        # Removed stockpile should be gone from cache
        assert "seaport:OtherHex:0.9_0.9:public" not in monitor._stockpile_cache


class TestSaveFileProcessorRun:
    """Test suite for SaveFileProcessor.run method."""

    @pytest.mark.asyncio
    async def test_run_processes_existing_file(self, tmp_path: Path) -> None:
        """Test run processes existing file on start."""
        save_file = tmp_path / "test.sav"
        save_file.touch()

        stockpile = Stockpile(
            name="Test",
            type=StockpileType.SEAPORT,
            items=[],
            timestamp=datetime.now(tz=UTC),
            raw_timestamp=100,
        )

        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = [stockpile]
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=save_file,
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=0.1,
        )

        # Run briefly then stop
        async def stop_after_delay() -> None:
            await asyncio.sleep(0.15)
            monitor.stop()

        await asyncio.gather(monitor.run(), stop_after_delay())

        # Should have processed the file
        mock_converter.convert_file.assert_called()

    @pytest.mark.asyncio
    async def test_run_detects_file_modification(self, tmp_path: Path) -> None:
        """Test run detects file modifications."""
        import time as time_module

        save_file = tmp_path / "test.sav"
        save_file.touch()

        stockpile = Stockpile(
            name="Test",
            type=StockpileType.SEAPORT,
            items=[],
            timestamp=datetime.now(tz=UTC),
            raw_timestamp=100,
        )

        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = [stockpile]
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=save_file,
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=0.05,
        )

        async def modify_and_stop() -> None:
            await asyncio.sleep(0.1)
            # Modify file to trigger reprocessing
            time_module.sleep(0.01)  # Ensure mtime changes
            save_file.write_text("modified")
            await asyncio.sleep(0.1)
            monitor.stop()

        await asyncio.gather(monitor.run(), modify_and_stop())

        # Should have processed the file multiple times
        assert mock_converter.convert_file.call_count >= 2

    @pytest.mark.asyncio
    async def test_run_handles_missing_file(self, tmp_path: Path) -> None:
        """Test run handles missing file gracefully."""
        save_file = tmp_path / "nonexistent.sav"

        mock_converter = MagicMock()
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=save_file,
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=0.05,
        )

        async def stop_after_delay() -> None:
            await asyncio.sleep(0.1)
            monitor.stop()

        await asyncio.gather(monitor.run(), stop_after_delay())

        # Should not have tried to process (file doesn't exist)
        mock_converter.convert_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_handles_errors_in_loop(self, tmp_path: Path) -> None:
        """Test run handles errors during loop iteration."""
        save_file = tmp_path / "test.sav"
        save_file.touch()

        mock_converter = MagicMock()
        mock_converter.convert_file.side_effect = Exception("Test error")
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=save_file,
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=0.05,
        )

        async def stop_after_delay() -> None:
            await asyncio.sleep(0.15)
            monitor.stop()

        # Should not raise despite errors
        await asyncio.gather(monitor.run(), stop_after_delay())

    @pytest.mark.asyncio
    async def test_run_cancelled(self, tmp_path: Path) -> None:
        """Test run handles cancellation gracefully."""
        save_file = tmp_path / "test.sav"
        save_file.touch()

        mock_converter = MagicMock()
        mock_converter.convert_file.return_value = []
        mock_coordinator = AsyncMock()

        monitor = SaveFileProcessor(
            file_path=save_file,
            converter=mock_converter,
            output_coordinator=mock_coordinator,
            poll_interval=0.05,
        )

        task = asyncio.create_task(monitor.run())
        await asyncio.sleep(0.1)
        task.cancel()

        # The run() method catches CancelledError and exits gracefully
        # So we just need to await and verify it completes without error
        try:
            await task
        except asyncio.CancelledError:
            pass  # This is acceptable too

        # Monitor should have stopped
        assert monitor.is_running is False


class TestMain:
    """Test suite for main() CLI function."""

    @pytest.mark.asyncio
    async def test_main_with_file_argument(self, tmp_path: Path) -> None:
        """Test main with --file argument."""
        save_file = tmp_path / "test_MapData.sav"
        save_file.touch()

        with patch("sys.argv", ["process-sav", "--file", str(save_file), "--once"]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                ) as mock_monitor_class:
                    mock_converter = MagicMock()
                    mock_converter_class.return_value = mock_converter

                    mock_monitor = MagicMock()
                    mock_monitor.run_once = AsyncMock()
                    mock_monitor_class.return_value = mock_monitor

                    await main()

                    mock_monitor.run_once.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_save_dir_argument(self, tmp_path: Path) -> None:
        """Test main with --save-dir argument."""
        save_file = tmp_path / "123_MapData.sav"
        save_file.touch()

        with patch("sys.argv", ["process-sav", "--save-dir", str(tmp_path), "--once"]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                ) as mock_monitor_class:
                    mock_converter = MagicMock()
                    mock_converter_class.return_value = mock_converter

                    mock_monitor = MagicMock()
                    mock_monitor.run_once = AsyncMock()
                    mock_monitor_class.return_value = mock_monitor

                    await main()

                    mock_monitor.run_once.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_save_dir_no_mapdata_file(self, tmp_path: Path) -> None:
        """Test main with --save-dir but no MapData.sav file."""
        with patch("sys.argv", ["process-sav", "--save-dir", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                await main()
            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_auto_detect_no_file(self) -> None:
        """Test main with auto-detection when no file found."""
        with patch("sys.argv", ["process-sav"]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav._get_default_savefile_path"
            ) as mock_get_default:
                mock_get_default.return_value = None

                with pytest.raises(SystemExit) as exc_info:
                    await main()
                assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_auto_detect_dir_not_exists(self) -> None:
        """Test main with auto-detection when default directory doesn't exist."""
        with patch("sys.argv", ["process-sav"]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav._get_default_savefile_path"
            ) as mock_get_default:
                mock_path = MagicMock()
                mock_path.exists.return_value = False
                mock_get_default.return_value = mock_path

                with pytest.raises(SystemExit) as exc_info:
                    await main()
                assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_file_not_exists(self, tmp_path: Path) -> None:
        """Test main when specified file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.sav"

        with patch("sys.argv", ["process-sav", "--file", str(nonexistent)]):
            with pytest.raises(SystemExit) as exc_info:
                await main()
            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_with_output_argument(self, tmp_path: Path) -> None:
        """Test main with --output argument overrides config."""
        save_file = tmp_path / "test_MapData.sav"
        save_file.touch()
        output_file = tmp_path / "output.json"

        with patch(
            "sys.argv",
            ["process-sav", "--file", str(save_file), "--output", str(output_file), "--once"],
        ):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                ) as mock_monitor_class:
                    with patch(
                        "foxhole_stockpiles.commands.process_sav.process_sav.OutputCoordinator"
                    ) as mock_coordinator_class:
                        mock_converter = MagicMock()
                        mock_converter_class.return_value = mock_converter

                        mock_monitor = MagicMock()
                        mock_monitor.run_once = AsyncMock()
                        mock_monitor_class.return_value = mock_monitor

                        await main()

                        # OutputCoordinator should be called with custom settings
                        mock_coordinator_class.assert_called_once()
                        call_args = mock_coordinator_class.call_args
                        output_settings = call_args[0][0]
                        assert len(output_settings.handlers) == 1
                        assert output_settings.handlers[0].handler.path == str(output_file)

    @pytest.mark.asyncio
    async def test_main_with_verbose_flag(self, tmp_path: Path) -> None:
        """Test main with --verbose flag."""
        save_file = tmp_path / "test_MapData.sav"
        save_file.touch()

        with patch("sys.argv", ["process-sav", "--file", str(save_file), "--verbose", "--once"]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                ) as mock_monitor_class:
                    with patch(
                        "foxhole_stockpiles.commands.process_sav.process_sav.setup_logging"
                    ) as mock_setup_logging:
                        mock_converter = MagicMock()
                        mock_converter_class.return_value = mock_converter

                        mock_monitor = MagicMock()
                        mock_monitor.run_once = AsyncMock()
                        mock_monitor_class.return_value = mock_monitor

                        await main()

                        # setup_logging should be called with DEBUG level
                        mock_setup_logging.assert_called_once()
                        call_args = mock_setup_logging.call_args
                        logging_settings = call_args[0][0]
                        assert logging_settings.log_level == "DEBUG"

    @pytest.mark.asyncio
    async def test_main_with_poll_interval(self, tmp_path: Path) -> None:
        """Test main with --poll-interval argument."""
        save_file = tmp_path / "test_MapData.sav"
        save_file.touch()

        with patch(
            "sys.argv",
            ["process-sav", "--file", str(save_file), "--poll-interval", "5.0", "--once"],
        ):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                ) as mock_monitor_class:
                    mock_converter = MagicMock()
                    mock_converter_class.return_value = mock_converter

                    mock_monitor = MagicMock()
                    mock_monitor.run_once = AsyncMock()
                    mock_monitor_class.return_value = mock_monitor

                    await main()

                    # SaveFileProcessor should be created with poll_interval=5.0
                    mock_monitor_class.assert_called_once()
                    call_kwargs = mock_monitor_class.call_args.kwargs
                    assert call_kwargs["poll_interval"] == 5.0

    @pytest.mark.asyncio
    async def test_main_converter_initialization_error(self, tmp_path: Path) -> None:
        """Test main handles converter FileNotFoundError."""
        save_file = tmp_path / "test_MapData.sav"
        save_file.touch()

        with patch("sys.argv", ["process-sav", "--file", str(save_file)]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                mock_converter_class.side_effect = FileNotFoundError("Catalog not found")

                with pytest.raises(SystemExit) as exc_info:
                    await main()
                assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_continuous_mode_with_keyboard_interrupt(self, tmp_path: Path) -> None:
        """Test main handles KeyboardInterrupt in continuous mode."""
        save_file = tmp_path / "test_MapData.sav"
        save_file.touch()

        with patch("sys.argv", ["process-sav", "--file", str(save_file)]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                ) as mock_monitor_class:
                    mock_converter = MagicMock()
                    mock_converter_class.return_value = mock_converter

                    mock_monitor = MagicMock()
                    mock_monitor.run = AsyncMock(side_effect=KeyboardInterrupt())
                    mock_monitor.stop = MagicMock()
                    mock_monitor_class.return_value = mock_monitor

                    # Should not raise, just handle gracefully
                    await main()

                    mock_monitor.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_config_argument(self, tmp_path: Path) -> None:
        """Test main with --config argument."""
        save_file = tmp_path / "test_MapData.sav"
        save_file.touch()
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        with patch(
            "sys.argv",
            ["process-sav", "--file", str(save_file), "--config", str(config_file), "--once"],
        ):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
            ) as mock_converter_class:
                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                ) as mock_monitor_class:
                    with patch(
                        "foxhole_stockpiles.commands.process_sav.process_sav.AppSettings"
                    ) as mock_app_settings:
                        with patch(
                            "foxhole_stockpiles.commands.process_sav.process_sav.setup_logging"
                        ):
                            mock_settings_instance = MagicMock()
                            mock_settings_instance.logging = MagicMock()
                            mock_settings_instance.logging.log_level = "INFO"
                            mock_settings_instance.output = MagicMock()
                            mock_app_settings.return_value = mock_settings_instance
                            mock_app_settings.model_config = {"env_file": None}

                            mock_converter = MagicMock()
                            mock_converter_class.return_value = mock_converter

                            mock_monitor = MagicMock()
                            mock_monitor.run_once = AsyncMock()
                            mock_monitor_class.return_value = mock_monitor

                            await main()

                            # AppSettings should have been instantiated
                            mock_app_settings.assert_called()

    @pytest.mark.asyncio
    async def test_main_auto_detect_finds_file(self, tmp_path: Path) -> None:
        """Test main with auto-detection when file is found."""
        save_file = tmp_path / "123_MapData.sav"
        save_file.touch()

        with patch("sys.argv", ["process-sav", "--once"]):
            with patch(
                "foxhole_stockpiles.commands.process_sav.process_sav._get_default_savefile_path"
            ) as mock_get_default:
                mock_get_default.return_value = tmp_path

                with patch(
                    "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileConverter"
                ) as mock_converter_class:
                    with patch(
                        "foxhole_stockpiles.commands.process_sav.process_sav.SaveFileProcessor"
                    ) as mock_monitor_class:
                        mock_converter = MagicMock()
                        mock_converter_class.return_value = mock_converter

                        mock_monitor = MagicMock()
                        mock_monitor.run_once = AsyncMock()
                        mock_monitor_class.return_value = mock_monitor

                        await main()

                        mock_monitor.run_once.assert_called_once()
