"""Tests for the ToolLauncherRow widget."""

from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyle, QWidget

from fs_tools.gui.widgets.tool_launcher_row import ToolLauncherRow


@pytest.fixture
def row(qtbot: Any) -> ToolLauncherRow:
    """Create a ToolLauncherRow with a standard icon.

    Args:
        qtbot: pytest-qt fixture.

    Returns:
        ToolLauncherRow: The row under test.
    """
    icon = QWidget().style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    widget = ToolLauncherRow(icon)
    qtbot.addWidget(widget)
    return widget


def test_set_text_updates_labels(row: ToolLauncherRow) -> None:
    """set_text populates the title and description labels.

    Args:
        row (ToolLauncherRow): The row under test.
    """
    row.set_text("My Tool", "Does something useful.")

    assert row._title_label.text() == "My Tool"
    assert row._description_label.text() == "Does something useful."


def test_left_click_emits_clicked(qtbot: Any, row: ToolLauncherRow) -> None:
    """A left-button click anywhere on the row emits clicked.

    Args:
        qtbot: pytest-qt fixture.
        row (ToolLauncherRow): The row under test.
    """
    row.resize(300, 60)
    row.show()
    qtbot.waitExposed(row)

    with qtbot.waitSignal(row.clicked, timeout=1000):
        qtbot.mouseClick(row, Qt.MouseButton.LeftButton)
