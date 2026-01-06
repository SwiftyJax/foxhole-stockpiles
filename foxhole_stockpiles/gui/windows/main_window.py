"""Main application window."""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from foxhole_stockpiles import __version__
from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.gui.widgets.server_control_panel import ServerControlPanel
from foxhole_stockpiles.gui.windows.config_window import ConfigWindow
from foxhole_stockpiles.gui.windows.database_info_window import DatabaseInfoWindow
from foxhole_stockpiles.gui.windows.icon_import_window import IconImportWindow

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        # Preference to minimize to tray on close (disabled by default)
        self.minimize_to_tray = False
        self.init_ui()
        self.create_tray_icon()

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
        if menu_bar is None:
            return

        # File menu
        file_menu = menu_bar.addMenu("&File")
        if file_menu is None:
            return

        config_action = file_menu.addAction("&Configuration...")
        if config_action is not None:
            config_action.triggered.connect(self.show_configuration)

        scan_action = file_menu.addAction("&Scan Screenshot...")
        if scan_action is not None:
            scan_action.triggered.connect(self.scan_screenshot)

        file_menu.addSeparator()

        minimize_to_tray_action = file_menu.addAction("Minimize to &Tray on Close")
        if minimize_to_tray_action is not None:
            minimize_to_tray_action.setCheckable(True)
            minimize_to_tray_action.setChecked(self.minimize_to_tray)
            minimize_to_tray_action.triggered.connect(self.toggle_minimize_to_tray)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("E&xit")
        if exit_action is not None:
            exit_action.triggered.connect(self.quit_application)

        # Database menu
        database_menu = menu_bar.addMenu("&Database")
        if database_menu is None:
            return

        build_database_action = database_menu.addAction("&Build...")
        if build_database_action is not None:
            build_database_action.triggered.connect(self.show_icon_import)

        info_database_action = database_menu.addAction("&Information...")
        if info_database_action is not None:
            info_database_action.triggered.connect(self.show_database_info)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        if help_menu is None:
            return
        about_action = help_menu.addAction("&About")
        if about_action is not None:
            about_action.triggered.connect(self.show_about)

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
            from PyQt6.QtCore import QSize
            from PyQt6.QtGui import QColor, QPainter, QPixmap

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

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        config_action = QAction("Configuration...", self)
        config_action.triggered.connect(self.show_configuration)
        tray_menu.addAction(config_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # Double-click to show window
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # Set tooltip
        self.tray_icon.setToolTip(f"FS (Foxhole Stockpiles) - v{__version__}")

        # Show tray icon and verify it's visible
        self.tray_icon.show()

        # Force processing of events to ensure tray icon is created
        from PyQt6.QtWidgets import QApplication

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

    def toggle_minimize_to_tray(self, checked: bool) -> None:
        """Toggle minimize to tray preference.

        Args:
            checked (bool): Whether minimize to tray is enabled
        """
        self.minimize_to_tray = checked
        logger.info(f"Minimize to tray: {self.minimize_to_tray}")

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

        # Connect to refresh DB info when config window closes
        config_window.destroyed.connect(self.server_panel.refresh_db_info)

        config_window.show()

    def show_icon_import(self) -> None:
        """Show icon import window as modal dialog centered on main window."""
        import_window = IconImportWindow(self)
        import_window.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Center the import window on the main window
        main_geometry = self.geometry()
        import_geometry = import_window.geometry()

        center_x = main_geometry.x() + (main_geometry.width() - import_geometry.width()) // 2
        center_y = main_geometry.y() + (main_geometry.height() - import_geometry.height()) // 2

        import_window.move(center_x, center_y)
        import_window.show()

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

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About FS",
            f"<h2>FS (Foxhole Stockpiles)</h2>"
            f"<p>Version {__version__}</p>"
            f"<p>A tool for scanning and analyzing Foxhole game stockpiles.</p>"
            f"<p><b>Features:</b></p>"
            f"<ul>"
            f"<li>Stockpile screenshot scanning</li>"
            f"<li>Template database management</li>"
            f"<li>FastAPI server for remote scanning</li>"
            f"</ul>"
            f"<p><b>Links:</b></p>"
            f"<p><a href='https://github.com/xurxogr/foxhole-stockpiles'>GitHub Repository</a></p>"
            f"<p><a href='https://github.com/xurxogr/foxhole-stockpiles-client'>"
            f"FS Client (Complementary Tool)</a></p>"
            f"<hr>"
            f"<p>Copyright © 2024 Xurxogr</p>"
            f"<p>Licensed under the MIT License</p>",
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
                    "FS - Foxhole Stockpiles",
                    "Application minimized to system tray. Right-click the tray icon for options.",
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
        from foxhole_stockpiles.gui.utils.qt_log_handler import QtLogHandler

        root_logger = logging.getLogger()
        handlers_to_remove = [h for h in root_logger.handlers[:] if isinstance(h, QtLogHandler)]

        for handler in handlers_to_remove:
            root_logger.removeHandler(handler)
            handler.close()

        # Hide tray icon
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

        # Close the application
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()
