"""Tests for DatabaseInfoWindow."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.gui.windows.database_info_window import DatabaseInfoWindow


@pytest.fixture
def hdf5_database_path() -> Path:
    """Get path to test HDF5 database.

    Returns:
        Path: Path to test HDF5 database file
    """
    return Path(__file__).parent.parent.parent / "fixtures" / "test_db_v1.h5"


@pytest.fixture
def info_window(qtbot: Any) -> DatabaseInfoWindow:
    """Create a DatabaseInfoWindow instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        DatabaseInfoWindow: Window instance
    """
    window = DatabaseInfoWindow()
    qtbot.addWidget(window)
    return window


def test_window_initialization(info_window: DatabaseInfoWindow) -> None:
    """Test DatabaseInfoWindow initialization.

    Args:
        info_window (DatabaseInfoWindow): Window instance
    """
    assert info_window.windowTitle() == "Database Information"
    assert info_window.db_path_input.text() == ""
    assert info_window.stats_table.rowCount() == 2  # Message rows


def test_window_with_initial_path(qtbot: Any, hdf5_database_path: Path) -> None:
    """Test DatabaseInfoWindow with initial database path.

    Args:
        qtbot: PyQt test fixture
        hdf5_database_path (Path): Test database path
    """
    window = DatabaseInfoWindow(initial_db_path=str(hdf5_database_path))
    qtbot.addWidget(window)

    assert window.db_path_input.text() == str(hdf5_database_path)
    # Should have loaded statistics automatically (at least one mod row)
    assert window.stats_table.rowCount() >= 1
    assert window.stats_table.columnCount() >= 2  # Mod + resolution columns


def test_browse_database(
    qtbot: Any, info_window: DatabaseInfoWindow, hdf5_database_path: Path
) -> None:
    """Test browsing for database file.

    Args:
        qtbot: PyQt test fixture
        info_window (DatabaseInfoWindow): Window instance
        hdf5_database_path (Path): Test database path
    """
    with patch(
        "foxhole_stockpiles.gui.windows.database_info_window.QFileDialog.getOpenFileName",
        return_value=(str(hdf5_database_path), ""),
    ):
        info_window.browse_database()

    assert info_window.db_path_input.text() == str(hdf5_database_path)
    # Statistics should be loaded automatically (at least one mod row)
    assert info_window.stats_table.rowCount() >= 1
    assert info_window.stats_table.columnCount() >= 2  # Mod + resolution columns


def test_load_statistics_valid_database(
    info_window: DatabaseInfoWindow, hdf5_database_path: Path
) -> None:
    """Test loading statistics from valid database.

    Args:
        info_window (DatabaseInfoWindow): Window instance
        hdf5_database_path (Path): Test database path
    """
    info_window.db_path_input.setText(str(hdf5_database_path))
    info_window.load_statistics()

    # Should have data rows (not just message rows)
    assert info_window.stats_table.rowCount() > 0
    assert info_window.stats_table.columnCount() > 1  # Mod + resolution columns


def test_load_statistics_no_path(info_window: DatabaseInfoWindow) -> None:
    """Test loading statistics with no path selected.

    Args:
        info_window (DatabaseInfoWindow): Window instance
    """
    info_window.load_statistics()

    # Should show error message
    assert info_window.stats_table.rowCount() == 2
    item = info_window.stats_table.item(0, 0)
    assert item is not None
    assert "No file selected" in item.text()


def test_load_statistics_nonexistent_file(info_window: DatabaseInfoWindow) -> None:
    """Test loading statistics from nonexistent file.

    Args:
        info_window (DatabaseInfoWindow): Window instance
    """
    info_window.db_path_input.setText("/nonexistent/database.h5")
    info_window.load_statistics()

    # Should show error message
    assert info_window.stats_table.rowCount() == 2
    item = info_window.stats_table.item(0, 0)
    assert item is not None
    assert "File not found" in item.text()


def test_load_statistics_displays_mods_and_resolutions(
    info_window: DatabaseInfoWindow, hdf5_database_path: Path
) -> None:
    """Test that statistics display mods and resolutions correctly.

    Args:
        info_window (DatabaseInfoWindow): Window instance
        hdf5_database_path (Path): Test database path
    """
    info_window.db_path_input.setText(str(hdf5_database_path))
    info_window.load_statistics()

    # Check headers
    headers = []
    for col in range(info_window.stats_table.columnCount()):
        item = info_window.stats_table.horizontalHeaderItem(col)
        if item:
            headers.append(item.text())

    assert "Mod" in headers
    # Should have resolution columns like "1080p", "1440p"
    assert any("p" in h for h in headers[1:])


def test_show_message(info_window: DatabaseInfoWindow) -> None:
    """Test showing message in table.

    Args:
        info_window (DatabaseInfoWindow): Window instance
    """
    info_window._show_message("Test Title", "Test Message")

    assert info_window.stats_table.rowCount() == 2
    title_item = info_window.stats_table.item(0, 0)
    assert title_item is not None
    assert title_item.text() == "Test Title"

    message_item = info_window.stats_table.item(1, 0)
    assert message_item is not None
    assert message_item.text() == "Test Message"


def test_load_statistics_error_handling(info_window: DatabaseInfoWindow, tmp_path: Path) -> None:
    """Test error handling when loading corrupted database.

    Args:
        info_window (DatabaseInfoWindow): Window instance
        tmp_path (Path): Temporary directory
    """
    # Create an invalid file
    bad_db = tmp_path / "bad.h5"
    bad_db.write_text("not a valid HDF5 file")

    info_window.db_path_input.setText(str(bad_db))
    info_window.load_statistics()

    # Should show error message
    assert info_window.stats_table.rowCount() == 2
    item = info_window.stats_table.item(0, 0)
    assert item is not None
    assert "Error" in item.text()
