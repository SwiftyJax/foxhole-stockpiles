"""Server control panel widget for managing the FastAPI server and scanning screenshots."""

import logging
from pathlib import Path

from pydantic import ValidationError
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.api.dependencies import clear_dependency_caches
from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.gui.utils.qt_log_handler import QtLogHandler
from foxhole_stockpiles.gui.utils.scan_worker import ScanWorker
from foxhole_stockpiles.gui.utils.scanner_client import ScannerClient
from foxhole_stockpiles.gui.utils.server_thread import ServerThread
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t
from foxhole_stockpiles.services.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class ServerControlPanel(QWidget):
    """Panel for controlling the FastAPI server and scanning screenshots."""

    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    screenshot_dropped = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the server control panel.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.server_running = False
        self.server_thread: ServerThread | None = None

        # Setup log handler and attach to root logger immediately
        # This allows capturing logs even before the server starts
        self.log_handler = QtLogHandler()
        self.log_handler.log_message.connect(self.append_log)
        self._attach_log_handler()

        # Setup scanner client
        self.scanner_client = ScannerClient()

        self.init_ui()

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

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Server Control section
        server_layout = QHBoxLayout()

        self.start_stop_button = QPushButton("Start Server")
        self.start_stop_button.clicked.connect(self.toggle_server)
        self.start_stop_button.setFixedWidth(120)
        server_layout.addWidget(self.start_stop_button)

        self.status_label = QLabel("Status: Stopped")
        self.status_label.setStyleSheet("QLabel { font-weight: bold; }")
        server_layout.addWidget(self.status_label)

        server_layout.addStretch()

        # DB info label (shown when valid)
        self.db_info_text = QLabel("")
        self.db_info_text.setStyleSheet("QLabel { font-size: 12px; }")
        self.db_info_text.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        server_layout.addWidget(self.db_info_text)

        layout.addLayout(server_layout)

        # Error panel (shown when config/DB invalid, replaces logs)
        self.error_panel = QLabel("")
        self.error_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_panel.setWordWrap(True)
        self.error_panel.setStyleSheet(
            "QLabel { "
            "border: 2px solid #FF9800; "
            "border-radius: 8px; "
            "background-color: palette(alternate-base); "
            "font-size: 13px; "
            "padding: 15px; "
            "}"
        )
        layout.addWidget(self.error_panel)

        # Server Logs Group (shown when everything valid)
        self.logs_group = QGroupBox("")
        logs_layout = QVBoxLayout()
        self.logs_group.setLayout(logs_layout)

        self.log_display = QTableWidget()
        self.log_display.setColumnCount(4)
        self.log_display.setHorizontalHeaderLabels(["Time", "Level", "Module", "Message"])
        self.log_display.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_display.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        vertical_header = self.log_display.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
        self.log_display.setStyleSheet(
            "QTableWidget { background-color: #1E1E1E; gridline-color: #3E3E3E; }"
        )

        # Set column widths
        header = self.log_display.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        # Set minimum column widths
        self.log_display.setColumnWidth(0, 150)  # Time
        self.log_display.setColumnWidth(1, 80)  # Level
        self.log_display.setColumnWidth(2, 250)  # Module

        logs_layout.addWidget(self.log_display)

        # Log controls
        log_controls = QHBoxLayout()
        self.clear_logs_button = QPushButton("")
        self.clear_logs_button.clicked.connect(self.clear_logs)
        log_controls.addStretch()
        log_controls.addWidget(self.clear_logs_button)
        logs_layout.addLayout(log_controls)

        layout.addWidget(self.logs_group)

        # Apply initial translations
        self.retranslate()

        # Initial validation
        self._update_validation_state()

    def refresh_db_info(self) -> None:
        """Refresh the database info and validation state."""
        self._update_validation_state()

    def on_database_updated(self, updated_db_path: Path) -> None:
        """Handle database file being updated.

        Called when the database builder successfully updates a database file.
        If the updated file matches the configured database, refresh the info
        and restart the server to pick up the changes.

        Args:
            updated_db_path: Path to the database file that was updated
        """
        # Check if the updated database is the one we're using
        try:
            settings = AppSettings()
            configured_path = settings.scanner.database_path
            if configured_path is None:
                return

            # Resolve both paths for comparison
            configured_resolved = Path(configured_path).resolve()
            updated_resolved = Path(updated_db_path).resolve()

            if configured_resolved != updated_resolved:
                return

            logger.info("Configured database was updated")

            # Refresh the database info display
            self._update_validation_state()

            # Restart server to pick up the new database
            if self.server_running:
                logger.info("Restarting server to load updated database...")
                self.stop_server()
                self.start_server()

        except Exception as e:
            logger.warning("Error checking database update: %s", e)

    def _update_validation_state(self) -> None:
        """Update the validation state and show/hide appropriate panels."""
        is_valid = False
        error_message = ""
        db_info = ""

        try:
            # Try to load config
            settings = AppSettings()
            db_path = settings.scanner.database_path

            if not db_path:
                error_message = (
                    f"<b>⚙️ {t('server_panel.errors.config_incomplete_title')}</b><br><br>"
                    f"{t('server_panel.errors.config_incomplete_message')}"
                )
            elif not Path(db_path).exists():
                error_message = (
                    f"<b>⚠️ {t('server_panel.errors.database_not_found_title')}</b><br><br>"
                    f"{t('server_panel.errors.database_not_found_message')}"
                )
            else:
                # Try to load DB statistics
                try:
                    manager = TemplateManager(database_path=Path(db_path))
                    stats = manager.get_database_statistics()

                    # Format mods list (comma-separated)
                    mods_text = ", ".join(sorted(stats.mod_stats.keys()))

                    # Determine path to display (relative if possible)
                    db_path_obj = Path(db_path)
                    try:
                        # Try to get relative path from current working directory
                        rel_path = db_path_obj.relative_to(Path.cwd())
                        display_path = str(rel_path)
                    except ValueError:
                        # Path is not relative to cwd, just show filename
                        display_path = db_path_obj.name

                    # Everything is valid
                    is_valid = True
                    db_info = f"Database: {display_path}  |  Mods: {mods_text}"

                except (FileNotFoundError, ValueError, OSError) as e:
                    # FileNotFoundError: database file missing
                    # ValueError: invalid database format
                    # OSError: database read error
                    logger.error(f"Failed to load database statistics: {e}")
                    error_message = (
                        f"<b>⚠️ {t('server_panel.errors.database_error_title')}</b><br><br>"
                        f"{t('server_panel.errors.database_error_message')}<br>"
                        f"<small>{str(e)[:100]}</small>"
                    )

        except (ValidationError, OSError, ValueError):
            # ValidationError: invalid config values
            # OSError: config file read error
            # ValueError: JSON decode error or invalid data
            error_message = (
                f"<b>⚙️ {t('server_panel.errors.no_config_title')}</b><br><br>"
                f"{t('server_panel.errors.no_config_message')}"
            )

        # Update UI based on validation state
        if is_valid:
            # Show DB info and logs, hide error panel
            self.db_info_text.setText(db_info)
            self.db_info_text.setVisible(True)
            self.error_panel.setVisible(False)
            self.logs_group.setVisible(True)
            self.start_stop_button.setEnabled(True)
        else:
            # Show error panel, hide DB info and logs
            self.error_panel.setText(error_message)
            self.error_panel.setVisible(True)
            self.db_info_text.setVisible(False)
            self.logs_group.setVisible(False)
            self.start_stop_button.setEnabled(False)

    def scan_screenshot_from_menu(self) -> None:
        """Open file dialog to select and scan a screenshot (called from menu)."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            t("server_panel.select_screenshot"),
            "",
            t("server_panel.image_filter"),
        )
        if filepath:
            self.process_screenshot(filepath)

    def toggle_server(self) -> None:
        """Toggle server start/stop."""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def _attach_log_handler(self) -> None:
        """Attach the Qt log handler to root logger if not already attached."""
        root_logger = logging.getLogger()

        # Check if our handler is already attached (by name)
        for handler in root_logger.handlers:
            if getattr(handler, "name", None) == QtLogHandler.HANDLER_NAME:
                return  # Already attached

        root_logger.addHandler(self.log_handler)

    def start_server(self) -> None:
        """Start the FastAPI server."""
        logger.info("Starting server...")

        # Create and start server thread
        self.server_thread = ServerThread()
        self.server_thread.start()

        self.server_running = True
        self.start_stop_button.setText(t("server_panel.stop_server"))
        self.status_label.setText(t("server_panel.status_running"))
        self.status_label.setStyleSheet("QLabel { font-weight: bold; color: green; }")
        self.server_started.emit()

    def stop_server(self) -> None:
        """Stop the FastAPI server."""
        logger.info("Stopping server...")

        # Stop server thread and wait for it to finish (allows lifespan cleanup)
        if self.server_thread:
            self.server_thread.stop()
            # Wait for server to finish shutdown (including sending notifications)
            self.server_thread.join(timeout=5.0)
            self.server_thread = None

        # Clear all dependency caches so next start picks up fresh settings
        clear_dependency_caches()

        # Note: Keep the log handler attached so we continue to see logs
        # even when the server is stopped

        self.server_running = False
        self.start_stop_button.setText(t("server_panel.start_server"))
        self.status_label.setText(t("server_panel.status_stopped"))
        self.status_label.setStyleSheet("QLabel { font-weight: bold; color: red; }")
        self.server_stopped.emit()

    def process_screenshot(self, filepath: str) -> None:
        """Process a screenshot file.

        Args:
            filepath (str): Path to the screenshot file
        """
        # Check if server is running
        if not self.server_running:
            logger.error(t("server_panel.errors.cannot_scan"))
            return

        # Scan the screenshot in background thread
        worker = ScanWorker(self.scanner_client, filepath)
        worker.finished.connect(lambda: self.screenshot_dropped.emit(filepath))
        worker.start()

        # Keep reference to prevent garbage collection
        if not hasattr(self, "_scan_workers"):
            self._scan_workers = []
        self._scan_workers.append(worker)
        worker.finished.connect(lambda: self._scan_workers.remove(worker))

    def append_log(self, log_data: dict[str, str]) -> None:
        """Append a log entry to the log display.

        Args:
            log_data (dict[str, str]): Dictionary containing timestamp, level, module, message,
                and color
        """
        row_position = self.log_display.rowCount()
        self.log_display.insertRow(row_position)

        color = QColor(log_data["color"])
        brush = QBrush(color)

        # Create table items
        time_item = QTableWidgetItem(log_data["timestamp"])
        time_item.setForeground(brush)

        level_item = QTableWidgetItem(log_data["level"])
        level_item.setForeground(brush)

        module_item = QTableWidgetItem(log_data["module"])
        module_item.setForeground(brush)

        message_item = QTableWidgetItem(log_data["message"])
        message_item.setForeground(brush)

        # Add items to table
        self.log_display.setItem(row_position, 0, time_item)
        self.log_display.setItem(row_position, 1, level_item)
        self.log_display.setItem(row_position, 2, module_item)
        self.log_display.setItem(row_position, 3, message_item)

        # Auto-scroll to bottom
        self.log_display.scrollToBottom()

    def clear_logs(self) -> None:
        """Clear the log display."""
        self.log_display.setRowCount(0)

    def retranslate(self) -> None:
        """Update all translatable strings."""
        # Button text depends on server state
        if self.server_running:
            self.start_stop_button.setText(t("server_panel.stop_server"))
            self.status_label.setText(t("server_panel.status_running"))
        else:
            self.start_stop_button.setText(t("server_panel.start_server"))
            self.status_label.setText(t("server_panel.status_stopped"))

        # Log table headers
        self.log_display.setHorizontalHeaderLabels(
            [
                t("server_panel.log_columns.time"),
                t("server_panel.log_columns.level"),
                t("server_panel.log_columns.module"),
                t("server_panel.log_columns.message"),
            ]
        )

        # Clear logs button
        self.clear_logs_button.setText(t("common.clear_logs"))
