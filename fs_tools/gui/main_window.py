"""Main window for the fs-tools desktop application.

Acts as a launcher: each tool opens its own window/dialog, reusing the
windows that previously lived in the main ``fs`` application.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles import __version__
from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t
from fs_tools.gui.windows.catalog_builder_window import CatalogBuilderWindow
from fs_tools.gui.windows.database_info_window import DatabaseInfoWindow
from fs_tools.gui.windows.database_visualizer_window import DatabaseVisualizerWindow
from fs_tools.gui.windows.debug_image_window import DebugImageWindow
from fs_tools.gui.windows.icon_import_window import IconImportWindow

logger = logging.getLogger(__name__)


class ToolsMainWindow(QMainWindow):
    """Launcher window for the Foxhole Stockpiles database tools."""

    def __init__(self) -> None:
        """Initialize the tools launcher window."""
        super().__init__()
        self.setGeometry(150, 150, 420, 360)

        # Keep references so launched windows are not garbage-collected.
        self._open_windows: list[QWidget] = []

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        self._icon_import_button = QPushButton()
        self._icon_import_button.clicked.connect(self.show_icon_import)
        layout.addWidget(self._icon_import_button)

        self._catalog_builder_button = QPushButton()
        self._catalog_builder_button.clicked.connect(self.show_catalog_builder)
        layout.addWidget(self._catalog_builder_button)

        self._visualizer_button = QPushButton()
        self._visualizer_button.clicked.connect(self.show_database_visualizer)
        layout.addWidget(self._visualizer_button)

        self._debug_viewer_button = QPushButton()
        self._debug_viewer_button.clicked.connect(self.show_debug_viewer)
        layout.addWidget(self._debug_viewer_button)

        self._database_info_button = QPushButton()
        self._database_info_button.clicked.connect(self.show_database_info)
        layout.addWidget(self._database_info_button)

        layout.addStretch(1)

        self.setCentralWidget(central)

        # Apply translations.
        self.retranslate()

        # Connect to language change signal with cleanup.
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)
        self.destroyed.connect(lambda cb=self._language_callback: off_language_changed(cb))

    def _on_language_changed(self, _language: str) -> None:
        """Handle a language change event.

        Args:
            _language (str): The newly selected language code (unused).
        """
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        self.setWindowTitle(t("tools_window.title", version=__version__))
        self._icon_import_button.setText(t("tools_window.buttons.icon_import"))
        self._catalog_builder_button.setText(t("tools_window.buttons.catalog_builder"))
        self._visualizer_button.setText(t("tools_window.buttons.visualizer"))
        self._debug_viewer_button.setText(t("tools_window.buttons.debug_viewer"))
        self._database_info_button.setText(t("tools_window.buttons.database_info"))

    def _configured_database_path(self) -> str | None:
        """Return the database path from settings, if configured.

        Returns:
            str | None: Configured database path or None when unavailable.
        """
        try:
            settings = AppSettings()
            if settings.scanner.database_path:
                return str(settings.scanner.database_path)
        except Exception as e:
            logger.warning(f"Could not read configured database path: {e}")
        return None

    def _require_database_path(self) -> str | None:
        """Return the configured database path or warn when missing.

        Returns:
            str | None: Configured database path, or None after warning the user.
        """
        database_path = self._configured_database_path()
        if not database_path:
            QMessageBox.warning(
                self,
                t("tools_window.no_database_title"),
                t("tools_window.no_database_message"),
            )
            return None
        return database_path

    def _track(self, window: QWidget) -> None:
        """Keep a reference to a launched window.

        Args:
            window (QWidget): The window to retain.
        """
        self._open_windows.append(window)
        window.destroyed.connect(lambda: self._open_windows.remove(window))

    def show_icon_import(self) -> None:
        """Open the icon import / database builder window."""
        window = IconImportWindow(self)
        self._track(window)
        window.show()

    def show_catalog_builder(self) -> None:
        """Open the catalog builder window."""
        window = CatalogBuilderWindow(self)
        self._track(window)
        window.show()

    def show_database_info(self) -> None:
        """Open the database information dialog."""
        window = DatabaseInfoWindow(self, initial_db_path=self._configured_database_path())
        window.setWindowModality(Qt.WindowModality.NonModal)
        self._track(window)
        window.show()

    def show_database_visualizer(self) -> None:
        """Open the database visualizer dialog."""
        database_path = self._require_database_path()
        if database_path is None:
            return
        window = DatabaseVisualizerWindow(self, database_path=database_path)
        window.setWindowModality(Qt.WindowModality.NonModal)
        self._track(window)
        window.show()

    def show_debug_viewer(self) -> None:
        """Open the debug image viewer dialog."""
        database_path = self._require_database_path()
        if database_path is None:
            return
        window = DebugImageWindow(self, database_path=database_path)
        window.setWindowModality(Qt.WindowModality.NonModal)
        self._track(window)
        window.show()
