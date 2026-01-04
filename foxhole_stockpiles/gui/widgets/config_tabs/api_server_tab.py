"""API Server settings tab."""

import json

from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.api import APIServerSettings


class APIServerTab(QWidget):
    """Tab for API Server configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the API Server tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QFormLayout(self)

        # Host
        host_label = QLabel("Host:")
        host_label.setToolTip(
            "IP address the API server will listen on.\n"
            "Use 127.0.0.1 for local-only access, or 0.0.0.0 to allow external connections."
        )
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("127.0.0.1")
        layout.addRow(host_label, self.host_input)

        # Port
        port_label = QLabel("Port:")
        port_label.setToolTip(
            "Port number the API server will listen on.\n"
            "Default: 8000. Must be between 1-65535.\n"
            "Make sure this port is not already in use by another application."
        )
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8000)
        layout.addRow(port_label, self.port_input)

        # Workers
        workers_label = QLabel("Workers:")
        workers_label.setToolTip(
            "Number of worker processes for the API server.\n"
            "More workers can handle more concurrent requests but use more memory.\n"
            "Recommended: 1 for single-user, 2-4 for multi-user scenarios."
        )
        self.workers_input = QSpinBox()
        self.workers_input.setRange(1, 32)
        self.workers_input.setValue(1)
        layout.addRow(workers_label, self.workers_input)

        # CORS Allow Origins
        cors_label = QLabel("CORS Allow Origins:")
        cors_label.setToolTip(
            "Cross-Origin Resource Sharing (CORS) allowed origins in JSON format.\n\n"
            'Use ["*"] to allow all origins (less secure but convenient).\n'
            'Use ["http://localhost:3000", "http://example.com"] to restrict to '
            "specific origins.\n\n"
            "Only needed if accessing the API from a web browser."
        )
        self.cors_input = QPlainTextEdit()
        self.cors_input.setPlaceholderText('["*"] or ["http://localhost:3000"]')
        self.cors_input.setMaximumHeight(80)
        layout.addRow(cors_label, self.cors_input)

        # Enable Memory Monitoring
        memory_label = QLabel("Memory Monitoring:")
        memory_label.setToolTip(
            "Enable memory usage monitoring for scan operations.\n\n"
            "When enabled, memory usage statistics will be logged for each scan.\n"
            "Useful for diagnosing memory issues, but adds slight overhead."
        )
        self.memory_monitoring_input = QCheckBox("Track memory usage")
        layout.addRow(memory_label, self.memory_monitoring_input)

        # Auto Trim Memory
        trim_label = QLabel("Auto Trim Memory:")
        trim_label.setToolTip(
            "Automatically release unused memory after each scan completes.\n\n"
            "Helps prevent memory accumulation during long-running sessions.\n"
            "Recommended: Enabled (may cause brief pauses after scans on some systems)."
        )
        self.auto_trim_input = QCheckBox("Automatically trim memory after scans")
        self.auto_trim_input.setChecked(True)
        layout.addRow(trim_label, self.auto_trim_input)

    def set_values(self, settings: APIServerSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (APIServerSettings): APIServerSettings instance to load values from.
        """
        self.host_input.setText(settings.host)
        self.port_input.setValue(settings.port)
        self.workers_input.setValue(settings.workers)

        # Convert list to JSON string for display
        cors_text = json.dumps(settings.cors_allow_origins, indent=2)
        self.cors_input.setPlainText(cors_text)

        self.memory_monitoring_input.setChecked(settings.enable_memory_monitoring)
        self.auto_trim_input.setChecked(settings.auto_trim_memory)

    def get_values(self) -> APIServerSettings:
        """Get current values from widgets.

        Returns:
            APIServerSettings: APIServerSettings instance with current values from widgets
        """
        # Parse CORS origins from text
        try:
            cors_origins = json.loads(self.cors_input.toPlainText())
        except json.JSONDecodeError:
            cors_origins = ["*"]

        return APIServerSettings(
            host=self.host_input.text(),
            port=self.port_input.value(),
            workers=self.workers_input.value(),
            cors_allow_origins=cors_origins,
            log_level="info",  # Use default, configured in Logging tab
            reload=False,  # Always False for GUI users (development-only option)
            enable_memory_monitoring=self.memory_monitoring_input.isChecked(),
            auto_trim_memory=self.auto_trim_input.isChecked(),
        )
