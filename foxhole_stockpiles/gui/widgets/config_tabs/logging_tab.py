"""Logging settings tab."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.logging import LoggingSettings
from foxhole_stockpiles.enums.config_level import ConfigLevel

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class CustomLoggerRowWidget(QWidget):
    """Widget for a custom logger entry with name, level dropdown, and remove button."""

    def __init__(
        self,
        logger_name: str,
        level: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the custom logger row widget.

        Args:
            logger_name: Name of the logger
            level: Log level for this logger
            parent: Parent widget
        """
        super().__init__(parent)
        self._removed = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Logger name input
        self.name_input = QLineEdit(logger_name)
        self.name_input.setPlaceholderText("e.g., uvicorn.access")
        layout.addWidget(self.name_input, 1)  # stretch factor 1

        # Level dropdown
        self.level_combo = QComboBox()
        self.level_combo.addItems(LOG_LEVELS)
        self.level_combo.setCurrentText(level.upper())
        self.level_combo.setFixedWidth(100)
        layout.addWidget(self.level_combo)

        # Remove button
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setFixedWidth(80)
        self.remove_btn.clicked.connect(self._on_remove)
        layout.addWidget(self.remove_btn)

    def _on_remove(self) -> None:
        """Handle remove button click."""
        self._removed = True
        self.setVisible(False)

    def is_removed(self) -> bool:
        """Check if this row was removed."""
        return self._removed

    def get_logger_name(self) -> str:
        """Get the logger name."""
        return self.name_input.text().strip()

    def get_level(self) -> str:
        """Get the selected log level."""
        return self.level_combo.currentText()


class LoggingTab(QWidget):
    """Tab for Logging configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Logging tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.custom_logger_rows: list[CustomLoggerRowWidget] = []
        # Track widgets that should be hidden at basic level
        self._advanced_widgets: list[QWidget] = []
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Form section for basic settings
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Root Log Level
        root_level_label = QLabel("Root Log Level:")
        root_level_label.setToolTip(
            "Global default log level for all loggers.\n\n"
            "Messages below this level are filtered out unless\n"
            "a custom logger overrides it."
        )
        self.root_level_combo = QComboBox()
        self.root_level_combo.addItems(LOG_LEVELS)
        self.root_level_combo.setCurrentText("INFO")
        form_layout.addRow(root_level_label, self.root_level_combo)

        # Log Format - ADVANCED
        self._log_format_label = QLabel("Log Format:")
        self._log_format_label.setToolTip(
            "Python logging format string.\n\n"
            "Common placeholders:\n"
            "• %(asctime)s - Timestamp\n"
            "• %(name)s - Logger name\n"
            "• %(levelname)s - Log level (DEBUG, INFO, etc.)\n"
            "• %(message)s - Log message\n\n"
            "See Python logging documentation for more options."
        )
        self.log_format_input = QLineEdit()
        self.log_format_input.setPlaceholderText(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        form_layout.addRow(self._log_format_label, self.log_format_input)
        self._advanced_widgets.extend([self._log_format_label, self.log_format_input])

        # Date Format - ADVANCED
        self._date_format_label = QLabel("Date Format:")
        self._date_format_label.setToolTip(
            "Date/time format for log timestamps.\n\n"
            "Uses Python strftime format codes:\n"
            "• %Y - 4-digit year\n"
            "• %m - 2-digit month\n"
            "• %d - 2-digit day\n"
            "• %H - 24-hour hour\n"
            "• %M - 2-digit minute\n"
            "• %S - 2-digit second\n\n"
            "Example: %Y-%m-%d %H:%M:%S produces 2025-01-15 14:30:45"
        )
        self.date_format_input = QLineEdit()
        self.date_format_input.setPlaceholderText("%Y-%m-%d %H:%M:%S")
        form_layout.addRow(self._date_format_label, self.date_format_input)
        self._advanced_widgets.extend([self._date_format_label, self.date_format_input])

        # Rotate Logs - ADVANCED
        self._rotate_logs_label = QLabel("Rotate Logs:")
        self._rotate_logs_label.setToolTip(
            "Automatically rotate log files when they get too large.\n\n"
            "When enabled, old logs are archived and new log files are created.\n"
            "Prevents log files from consuming too much disk space."
        )
        self.rotate_logs_input = QCheckBox("Enable log rotation")
        form_layout.addRow(self._rotate_logs_label, self.rotate_logs_input)
        self._advanced_widgets.extend([self._rotate_logs_label, self.rotate_logs_input])

        # Log File - ADVANCED
        self._log_file_label = QLabel("Log File:")
        self._log_file_label.setToolTip(
            "Optional path to save log messages to a file.\n\n"
            "If not specified, logs are only written to console.\n"
            "Useful for debugging and keeping a record of operations."
        )
        self._log_file_widget = QWidget()
        log_file_layout = QHBoxLayout(self._log_file_widget)
        log_file_layout.setContentsMargins(0, 0, 0, 0)
        self.log_file_input = QLineEdit()
        self.log_file_input.setPlaceholderText("Optional: path to log file")
        log_browse = QPushButton("Browse...")
        log_browse.clicked.connect(self._browse_log_file)
        log_file_layout.addWidget(self.log_file_input)
        log_file_layout.addWidget(log_browse)
        form_layout.addRow(self._log_file_label, self._log_file_widget)
        self._advanced_widgets.extend([self._log_file_label, self._log_file_widget])

        layout.addLayout(form_layout)

        # Custom Log Levels header with Add button - ADVANCED
        self._custom_loggers_header = QWidget()
        header_layout = QHBoxLayout(self._custom_loggers_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        custom_loggers_label = QLabel("Custom Log Levels:")
        custom_loggers_label.setToolTip(
            "Override log levels for specific loggers.\n\n"
            "Common loggers:\n"
            "• uvicorn - Web server logs\n"
            "• uvicorn.access - HTTP request logs\n"
            "• foxhole_stockpiles - Application logs"
        )
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_add_logger)
        header_layout.addWidget(custom_loggers_label)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)
        layout.addWidget(self._custom_loggers_header)
        self._advanced_widgets.append(self._custom_loggers_header)

        # Scroll area for custom logger rows (expands to fill remaining space) - ADVANCED
        self._loggers_scroll = QScrollArea()
        self._loggers_scroll.setWidgetResizable(True)

        self.loggers_container = QWidget()
        self.loggers_list_layout = QVBoxLayout(self.loggers_container)
        self.loggers_list_layout.setContentsMargins(0, 0, 0, 0)
        self.loggers_list_layout.setSpacing(4)
        self.loggers_list_layout.addStretch()

        self._loggers_scroll.setWidget(self.loggers_container)
        layout.addWidget(self._loggers_scroll, 1)  # stretch factor 1 to fill space
        self._advanced_widgets.append(self._loggers_scroll)

    def set_config_level(self, level: ConfigLevel) -> None:
        """Show or hide fields based on the configuration level.

        Args:
            level (ConfigLevel): The configuration level to set.
        """
        # Advanced widgets are visible at advanced and developer levels
        for widget in self._advanced_widgets:
            widget.setVisible(level.is_at_least(ConfigLevel.ADVANCED))

    def _add_custom_logger_row(self, logger_name: str, level: str) -> CustomLoggerRowWidget:
        """Add a custom logger row to the list.

        Args:
            logger_name: Name of the logger
            level: Log level

        Returns:
            The created CustomLoggerRowWidget
        """
        row = CustomLoggerRowWidget(logger_name, level)
        self.custom_logger_rows.append(row)
        # Insert before the stretch
        self.loggers_list_layout.insertWidget(self.loggers_list_layout.count() - 1, row)
        return row

    def _on_add_logger(self) -> None:
        """Handle add logger button click."""
        self._add_custom_logger_row("", "INFO")

    def _browse_log_file(self) -> None:
        """Open file dialog for log file path."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File",
            "",
            "Log Files (*.log);;All Files (*)",
        )
        if filepath:
            self.log_file_input.setText(filepath)

    def _clear_custom_logger_rows(self) -> None:
        """Clear all custom logger rows (for reloading)."""
        for row in self.custom_logger_rows:
            row.setParent(None)
            row.deleteLater()
        self.custom_logger_rows.clear()

    def set_values(self, settings: LoggingSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (LoggingSettings): LoggingSettings instance to load values from.
        """
        # Set root log level
        self.root_level_combo.setCurrentText(settings.log_level.upper())

        # Set other values
        self.log_format_input.setText(settings.log_format)
        self.date_format_input.setText(settings.date_format)
        self.rotate_logs_input.setChecked(settings.rotate_logs)
        self.log_file_input.setText(str(settings.log_file) if settings.log_file else "")

        # Clear existing custom logger rows and recreate
        self._clear_custom_logger_rows()

        # Add custom loggers from settings
        for logger_name, level in settings.loggers.items():
            self._add_custom_logger_row(logger_name, level)

    def get_values(self) -> LoggingSettings:
        """Get current values from widgets.

        Returns:
            LoggingSettings: LoggingSettings instance with current values from widgets
        """
        # Get root log level
        log_level = self.root_level_combo.currentText()

        # Collect custom logger levels
        loggers: dict[str, str] = {}
        for row in self.custom_logger_rows:
            if row.is_removed():
                continue

            name = row.get_logger_name()
            level = row.get_level()

            if not name:
                continue

            loggers[name] = level

        return LoggingSettings(
            log_level=log_level,
            loggers=loggers,
            log_format=self.log_format_input.text(),
            date_format=self.date_format_input.text(),
            rotate_logs=self.rotate_logs_input.isChecked(),
            log_file=self.log_file_input.text() or None,
        )
