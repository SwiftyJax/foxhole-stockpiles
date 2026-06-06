"""Shared pytest fixtures for fs_tools tests.

Re-exports the project-wide fixtures defined in ``tests/conftest.py`` so the
moved fs_tools tests keep access to them.
"""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from foxhole_stockpiles.i18n import get_translator, set_translations_resource
from tests.conftest import (  # noqa: F401
    mock_catalog_file,
    mock_color_image_array,
    mock_discord_webhook,
    mock_image_array,
    mock_pak_file,
    reset_logging,
    sample_catalog_data,
    temp_dir,
)

_MAIN_TRANSLATIONS = "foxhole_stockpiles/i18n/translations"
_TOOLS_TRANSLATIONS = "fs_tools/i18n/translations"


@pytest.fixture(autouse=True)
def block_native_dialogs() -> Iterator[None]:
    """Stub out blocking native dialogs so tests never pop a real window.

    GUI code calls ``QMessageBox`` / ``QFileDialog`` static methods that open
    modal, blocking dialogs. Without this, any test that exercises such a path
    without explicitly patching the call would hang waiting for user input.
    Defaults model a "cancelled / no" interaction; tests that need a specific
    result patch the call locally, which overrides these stubs.

    Yields:
        None: Control to the test while the dialog stubs are active.
    """
    with (
        patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok),
        patch.object(QMessageBox, "critical", return_value=QMessageBox.StandardButton.Ok),
        patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok),
        patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No),
        patch.object(QFileDialog, "getOpenFileName", return_value=("", "")),
        patch.object(QFileDialog, "getOpenFileNames", return_value=([], "")),
        patch.object(QFileDialog, "getSaveFileName", return_value=("", "")),
        patch.object(QFileDialog, "getExistingDirectory", return_value=""),
    ):
        yield


@pytest.fixture(autouse=True)
def fs_tools_translations() -> Iterator[None]:
    """Point the shared translator at the fs_tools catalog for the duration of a test.

    fs_tools ships its own self-contained translation catalog; its windows use
    keys (tools_window, catalog_builder, ...) that no longer exist in the main
    foxhole_stockpiles catalog. This mirrors what ``fs_tools.gui._bootstrap`` does
    at runtime, and restores the default afterwards so main-app tests are unaffected.

    Yields:
        None: Control to the test while the fs_tools catalog is active.
    """
    set_translations_resource(_TOOLS_TRANSLATIONS)
    get_translator("en")
    try:
        yield
    finally:
        set_translations_resource(_MAIN_TRANSLATIONS)
        get_translator("en")
