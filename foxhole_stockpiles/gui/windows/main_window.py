"""Main application window."""

import logging

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from foxhole_stockpiles import __version__
from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.enums.config_level import ConfigLevel
from foxhole_stockpiles.gui.utils.qt_log_handler import QtLogHandler
from foxhole_stockpiles.gui.widgets.server_control_panel import ServerControlPanel
from foxhole_stockpiles.gui.windows.catalog_builder_window import CatalogBuilderWindow
from foxhole_stockpiles.gui.windows.config_window import ConfigWindow
from foxhole_stockpiles.gui.windows.database_info_window import DatabaseInfoWindow
from foxhole_stockpiles.gui.windows.database_visualizer_window import DatabaseVisualizerWindow
from foxhole_stockpiles.gui.windows.icon_import_window import IconImportWindow
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        # Load minimize_to_tray preference from config (default: False)
        self.minimize_to_tray = self._load_minimize_to_tray_setting()
        # Track menu actions that should be hidden based on config level
        self._advanced_menu_actions: list[QAction] = []
        self.init_ui()
        self.create_tray_icon()
        # Apply config level to menu visibility
        self._apply_config_level_to_menus()
        # Connect to language changes with cleanup on destruction
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)
        self.destroyed.connect(lambda: off_language_changed(self._language_callback))

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event.

        Args:
            _language: The new language code (unused).
        """
        self.retranslate()

    def _load_minimize_to_tray_setting(self) -> bool:
        """Load minimize_to_tray setting from config.

        Returns:
            bool: The minimize_to_tray setting value
        """
        try:
            settings = AppSettings()
            return settings.gui.minimize_to_tray
        except Exception as e:
            logger.warning(f"Failed to load minimize_to_tray setting: {e}")
            return False

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle(f"FS (Foxhole Stockpiles) - v{__version__}")
        self.setGeometry(100, 100, 1000, 700)

        # Create central widget with server control panel
        self.server_panel = ServerControlPanel()
        self.setCentralWidget(self.server_panel)

        # Create menu bar
        self.create_menu_bar()

    def create_menu_bar(self) -> None:
        """Create the menu bar."""
        menu_bar = self.menuBar()

        # File menu
        self.file_menu = menu_bar.addMenu("")  # type: ignore[union-attr]

        self.config_action = self.file_menu.addAction("")  # type: ignore[union-attr]
        self.config_action.triggered.connect(self.show_configuration)  # type: ignore[union-attr]

        self.scan_action = self.file_menu.addAction("")  # type: ignore[union-attr]
        self.scan_action.triggered.connect(self.scan_screenshot)  # type: ignore[union-attr]

        # Build Catalog - hidden at Basic config level
        self.build_catalog_action = self.file_menu.addAction("")  # type: ignore[union-attr]
        self.build_catalog_action.triggered.connect(self.show_catalog_builder)  # type: ignore[union-attr]
        self._advanced_menu_actions.append(self.build_catalog_action)  # type: ignore[arg-type]

        self.file_menu.addSeparator()  # type: ignore[union-attr]

        self.exit_action = self.file_menu.addAction("")  # type: ignore[union-attr]
        self.exit_action.triggered.connect(self.quit_application)  # type: ignore[union-attr]

        # Database menu
        self.database_menu = menu_bar.addMenu("")  # type: ignore[union-attr]

        # Build Database - hidden at Basic config level
        self.build_database_action = self.database_menu.addAction("")  # type: ignore[union-attr]
        self.build_database_action.triggered.connect(self.show_icon_import)  # type: ignore[union-attr]
        self._advanced_menu_actions.append(self.build_database_action)  # type: ignore[arg-type]

        self.info_database_action = self.database_menu.addAction("")  # type: ignore[union-attr]
        self.info_database_action.triggered.connect(self.show_database_info)  # type: ignore[union-attr]

        # Visualizer - hidden at Basic config level
        self.visualizer_action = self.database_menu.addAction("")  # type: ignore[union-attr]
        self.visualizer_action.triggered.connect(self.show_database_visualizer)  # type: ignore[union-attr]
        self._advanced_menu_actions.append(self.visualizer_action)  # type: ignore[arg-type]

        # Help menu
        self.help_menu = menu_bar.addMenu("")  # type: ignore[union-attr]
        self.about_action = self.help_menu.addAction("")  # type: ignore[union-attr]
        self.about_action.triggered.connect(self.show_about)  # type: ignore[union-attr]

        # Apply initial translations
        self.retranslate()

    def _apply_config_level_to_menus(self) -> None:
        """Apply config level settings to menu visibility."""
        try:
            settings = AppSettings()
            config_level = settings.gui.config_level
            # Advanced menu actions are visible at advanced and developer levels
            for action in self._advanced_menu_actions:
                action.setVisible(config_level.is_at_least(ConfigLevel.ADVANCED))
        except Exception as e:
            logger.warning(f"Failed to apply config level to menus: {e}")

    def create_tray_icon(self) -> None:
        """Create system tray icon with menu."""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this system")
            self.minimize_to_tray = False
            return

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)

        # Create a visible icon for Windows - use a standard pixmap that works cross-platform
        # Try multiple fallbacks to ensure we get a visible icon
        style = self.style()
        if style is not None:
            icon = style.standardIcon(style.StandardPixmap.SP_ComputerIcon)
        else:
            icon = QIcon()

        # On Windows, if the icon is still null, create a simple colored pixmap
        if icon.isNull():
            pixmap = QPixmap(QSize(64, 64))
            pixmap.fill(QColor(0, 120, 215))  # Blue color
            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "FS")
            painter.end()
            icon = QIcon(pixmap)

        self.tray_icon.setIcon(icon)
        logger.info("Created tray icon")

        # Create tray menu
        tray_menu = QMenu()

        self.tray_show_action = QAction("", self)
        self.tray_show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(self.tray_show_action)

        self.tray_hide_action = QAction("", self)
        self.tray_hide_action.triggered.connect(self.hide)
        tray_menu.addAction(self.tray_hide_action)

        tray_menu.addSeparator()

        self.tray_config_action = QAction("", self)
        self.tray_config_action.triggered.connect(self.show_configuration)
        tray_menu.addAction(self.tray_config_action)

        tray_menu.addSeparator()

        self.tray_quit_action = QAction("", self)
        self.tray_quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(self.tray_quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # Apply translations to tray menu
        self._retranslate_tray()

        # Double-click to show window
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # Set tooltip
        self.tray_icon.setToolTip(f"FS (Foxhole Stockpiles) - v{__version__}")

        # Show tray icon and verify it's visible
        self.tray_icon.show()

        # Force processing of events to ensure tray icon is created
        QApplication.processEvents()

        # Log tray icon visibility status
        logger.info(f"Tray icon visible: {self.tray_icon.isVisible()}")
        if not self.tray_icon.isVisible():
            logger.warning(
                "Tray icon created but not visible. "
                "It might be in the Windows overflow area (click ^ in system tray)"
            )

    def tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation.

        Args:
            reason (QSystemTrayIcon.ActivationReason): Activation reason
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()

    def show_from_tray(self) -> None:
        """Show window from system tray."""
        self.show()
        self.activateWindow()
        self.raise_()

    def scan_screenshot(self) -> None:
        """Open file dialog to scan a screenshot."""
        self.server_panel.scan_screenshot_from_menu()

    def show_configuration(self) -> None:
        """Show configuration window as modal dialog centered on main window."""
        config_window = ConfigWindow(self)
        config_window.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Center the config window on the main window
        main_geometry = self.geometry()
        config_geometry = config_window.geometry()

        center_x = main_geometry.x() + (main_geometry.width() - config_geometry.width()) // 2
        center_y = main_geometry.y() + (main_geometry.height() - config_geometry.height()) // 2

        config_window.move(center_x, center_y)

        # Connect to refresh DB info and settings when config window closes
        config_window.closed.connect(self.server_panel.refresh_db_info)
        config_window.closed.connect(self._on_config_closed)

        config_window.show()

    def _on_config_closed(self) -> None:
        """Handle config window closed - refresh settings from config."""
        # Reload minimize_to_tray setting
        self.minimize_to_tray = self._load_minimize_to_tray_setting()
        # Refresh menu visibility based on config level
        self._apply_config_level_to_menus()
        logger.info(f"Config reloaded - minimize_to_tray: {self.minimize_to_tray}")

    def show_icon_import(self) -> None:
        """Show icon import window as modal dialog centered on main window."""
        import_window = IconImportWindow(self)
        import_window.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Connect signal to handle database updates
        import_window.database_updated.connect(self.server_panel.on_database_updated)

        # Center the import window on the main window
        main_geometry = self.geometry()
        import_geometry = import_window.geometry()

        center_x = main_geometry.x() + (main_geometry.width() - import_geometry.width()) // 2
        center_y = main_geometry.y() + (main_geometry.height() - import_geometry.height()) // 2

        import_window.move(center_x, center_y)
        import_window.show()

    def show_catalog_builder(self) -> None:
        """Show catalog builder window as modal dialog centered on main window."""
        catalog_window = CatalogBuilderWindow(self)
        catalog_window.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Center the catalog window on the main window
        main_geometry = self.geometry()
        catalog_geometry = catalog_window.geometry()

        center_x = main_geometry.x() + (main_geometry.width() - catalog_geometry.width()) // 2
        center_y = main_geometry.y() + (main_geometry.height() - catalog_geometry.height()) // 2

        catalog_window.move(center_x, center_y)
        catalog_window.show()

    def show_database_info(self) -> None:
        """Show database information window."""
        # Try to get configured database path
        initial_db_path = None
        try:
            settings = AppSettings()
            if settings.scanner.database_path:
                initial_db_path = str(settings.scanner.database_path)
        except Exception:
            pass  # No config or error loading, will start with empty

        info_window = DatabaseInfoWindow(self, initial_db_path=initial_db_path)

        # Center the info window on the main window
        main_geometry = self.geometry()
        info_geometry = info_window.geometry()

        center_x = main_geometry.x() + (main_geometry.width() - info_geometry.width()) // 2
        center_y = main_geometry.y() + (main_geometry.height() - info_geometry.height()) // 2

        info_window.move(center_x, center_y)
        info_window.exec()

    def show_database_visualizer(self) -> None:
        """Show database visualizer window."""
        # Try to get configured database path
        database_path = None
        try:
            settings = AppSettings()
            if settings.scanner.database_path:
                database_path = str(settings.scanner.database_path)
        except Exception:
            pass  # No config or error loading

        if not database_path:
            QMessageBox.warning(
                self,
                t("main_window.dialogs.no_database_title"),
                t("main_window.dialogs.no_database_message"),
            )
            return

        visualizer_window = DatabaseVisualizerWindow(self, database_path=database_path)

        # Center the visualizer window on the main window
        main_geometry = self.geometry()
        visualizer_geometry = visualizer_window.geometry()

        center_x = main_geometry.x() + (main_geometry.width() - visualizer_geometry.width()) // 2
        center_y = main_geometry.y() + (main_geometry.height() - visualizer_geometry.height()) // 2

        visualizer_window.move(center_x, center_y)
        visualizer_window.exec()

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            t("about.title"),
            f"<h2>{t('about.app_name')}</h2>"
            f"<p>{t('about.version').replace('{version}', __version__)}</p>"
            f"<p>{t('about.description')}</p>"
            f"<p><b>{t('about.features_title')}</b></p>"
            f"<ul>"
            f"<li>{t('about.feature_scanning')}</li>"
            f"<li>{t('about.feature_database')}</li>"
            f"<li>{t('about.feature_server')}</li>"
            f"</ul>"
            f"<p><b>{t('about.links_title')}</b></p>"
            f"<p><a href='https://github.com/xurxogr/foxhole-stockpiles'>{t('about.github_link')}</a></p>"
            f"<p><a href='https://github.com/xurxogr/foxhole-stockpiles-client'>"
            f"{t('about.client_link')}</a></p>"
            f"<hr>"
            f"<p>{t('about.copyright')}</p>"
            f"<p>{t('about.license')}</p>",
        )

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Handle window close event.

        If minimize to tray is enabled, hide to tray instead of closing.
        Otherwise, perform cleanup and close.

        Args:
            event (QCloseEvent | None): Close event
        """
        if not event:
            return

        # Check if we can minimize to tray
        can_minimize_to_tray = (
            self.minimize_to_tray
            and hasattr(self, "tray_icon")
            and self.tray_icon is not None
            and self.tray_icon.isVisible()
        )

        if can_minimize_to_tray:
            logger.info("Minimizing to system tray")
            event.ignore()
            self.hide()

            # Show notification on first minimize
            if not hasattr(self, "_shown_tray_message"):
                self.tray_icon.showMessage(
                    t("main_window.tray.minimized_title"),
                    t("main_window.tray.minimized_message"),
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
                self._shown_tray_message = True
                logger.info(
                    "Note: On Windows, the tray icon might be in the overflow area. "
                    "Click the ^ arrow in the system tray to see hidden icons."
                )
        else:
            # Can't minimize to tray or it's disabled - actually quit
            if self.minimize_to_tray and not can_minimize_to_tray:
                logger.warning(
                    "Cannot minimize to tray (tray icon not available). Quitting instead."
                )
            self.quit_application()
            event.accept()

    def quit_application(self) -> None:
        """Quit the application with proper cleanup."""
        logger.info("Quitting application")

        # Stop server if running
        if hasattr(self, "server_panel") and self.server_panel.server_running:
            logger.info("Stopping server before quit")
            self.server_panel.stop_server()

        # Remove all QtLogHandler instances from all loggers before Qt cleanup
        root_logger = logging.getLogger()
        handlers_to_remove = [h for h in root_logger.handlers[:] if isinstance(h, QtLogHandler)]

        for handler in handlers_to_remove:
            root_logger.removeHandler(handler)
            handler.close()

        # Hide tray icon
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

        # Close the application
        QApplication.quit()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        # Window title
        self.setWindowTitle(t("main_window.title", version=__version__))

        # File menu
        self.file_menu.setTitle(t("main_window.menu.file"))  # type: ignore[union-attr]
        self.config_action.setText(t("main_window.menu.configuration"))  # type: ignore[union-attr]
        self.scan_action.setText(t("main_window.menu.scan_screenshot"))  # type: ignore[union-attr]
        self.build_catalog_action.setText(t("main_window.menu.build_catalog"))  # type: ignore[union-attr]
        self.exit_action.setText(t("main_window.menu.exit"))  # type: ignore[union-attr]

        # Database menu
        self.database_menu.setTitle(t("main_window.menu.database"))  # type: ignore[union-attr]
        self.build_database_action.setText(t("main_window.menu.build"))  # type: ignore[union-attr]
        self.info_database_action.setText(t("main_window.menu.information"))  # type: ignore[union-attr]
        self.visualizer_action.setText(t("main_window.menu.visualizer"))  # type: ignore[union-attr]

        # Help menu
        self.help_menu.setTitle(t("main_window.menu.help"))  # type: ignore[union-attr]
        self.about_action.setText(t("main_window.menu.about"))  # type: ignore[union-attr]

        # Tray menu (if available)
        self._retranslate_tray()

    def _retranslate_tray(self) -> None:
        """Update tray menu translations."""
        if hasattr(self, "tray_show_action"):
            self.tray_show_action.setText(t("main_window.tray.show"))
            self.tray_hide_action.setText(t("main_window.tray.hide"))
            self.tray_config_action.setText(t("main_window.tray.configuration"))
            self.tray_quit_action.setText(t("main_window.tray.quit"))
        if hasattr(self, "tray_icon"):
            self.tray_icon.setToolTip(t("main_window.title", version=__version__))
