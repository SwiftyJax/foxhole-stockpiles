"""API Server settings tab."""

import json

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.api import APIAuthSettings, APIServerSettings
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.config_level import ConfigLevel


class APIServerTab(QWidget):
    """Tab for API Server configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the API Server tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        # Track widgets that should be hidden at basic level
        self._advanced_widgets: list[QWidget] = []
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Server Settings Group
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        server_group.setLayout(server_layout)

        # Host
        host_label = QLabel("Host:")
        host_label.setToolTip(
            "IP address the API server will listen on.\n"
            "Use 127.0.0.1 for local-only access, or 0.0.0.0 to allow external connections."
        )
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("127.0.0.1")
        server_layout.addRow(host_label, self.host_input)

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
        server_layout.addRow(port_label, self.port_input)

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
        server_layout.addRow(workers_label, self.workers_input)

        # CORS Allow Origins - ADVANCED
        self._cors_label = QLabel("CORS Allow Origins:")
        self._cors_label.setToolTip(
            "Cross-Origin Resource Sharing (CORS) allowed origins in JSON format.\n\n"
            'Use ["*"] to allow all origins (less secure but convenient).\n'
            'Use ["http://localhost:3000", "http://example.com"] to restrict to '
            "specific origins.\n\n"
            "Only needed if accessing the API from a web browser."
        )
        self.cors_input = QPlainTextEdit()
        self.cors_input.setPlaceholderText('["*"] or ["http://localhost:3000"]')
        self.cors_input.setMaximumHeight(80)
        server_layout.addRow(self._cors_label, self.cors_input)
        self._advanced_widgets.extend([self._cors_label, self.cors_input])

        # Enable Memory Monitoring
        memory_label = QLabel("Memory Monitoring:")
        memory_label.setToolTip(
            "Enable memory usage monitoring for scan operations.\n\n"
            "When enabled, memory usage statistics will be logged for each scan.\n"
            "Useful for diagnosing memory issues, but adds slight overhead."
        )
        self.memory_monitoring_input = QCheckBox("Track memory usage")
        server_layout.addRow(memory_label, self.memory_monitoring_input)

        # Auto Trim Memory
        trim_label = QLabel("Auto Trim Memory:")
        trim_label.setToolTip(
            "Automatically release unused memory after each scan completes.\n\n"
            "Helps prevent memory accumulation during long-running sessions.\n"
            "Recommended: Enabled (may cause brief pauses after scans on some systems)."
        )
        self.auto_trim_input = QCheckBox("Automatically trim memory after scans")
        self.auto_trim_input.setChecked(True)
        server_layout.addRow(trim_label, self.auto_trim_input)

        # Web Icon Mod
        web_icon_mod_label = QLabel("Web Icon Mod:")
        web_icon_mod_label.setToolTip(
            "Mod to use for item icons in the web interface.\n\n"
            "When the web interface displays scan results, icons will be loaded\n"
            "from this mod. If an icon is not found in the specified mod,\n"
            "it will fall back to 'vanilla'.\n\n"
            "Available mods depend on what you've imported into the database."
        )
        self.web_icon_mod_input = QLineEdit()
        self.web_icon_mod_input.setPlaceholderText("vanilla")
        server_layout.addRow(web_icon_mod_label, self.web_icon_mod_input)

        layout.addWidget(server_group)

        # Authentication Group
        auth_group = QGroupBox("Authentication")
        auth_layout = QVBoxLayout()
        auth_group.setLayout(auth_layout)

        # Auth Type Selection with Radio Buttons
        auth_type_layout = QHBoxLayout()

        self.auth_type_button_group = QButtonGroup(self)

        self.no_auth_radio = QRadioButton("No Authentication")
        self.no_auth_radio.setChecked(True)
        self.no_auth_radio.setToolTip(
            "API server will accept requests from anyone without authentication."
        )
        self.auth_type_button_group.addButton(self.no_auth_radio, 0)
        auth_type_layout.addWidget(self.no_auth_radio)

        self.basic_auth_radio = QRadioButton("Basic Auth")
        self.basic_auth_radio.setToolTip(
            "Require username and password for API access.\n"
            "Credentials are sent with each request in the Authorization header."
        )
        self.auth_type_button_group.addButton(self.basic_auth_radio, 1)
        auth_type_layout.addWidget(self.basic_auth_radio)

        self.bearer_auth_radio = QRadioButton("Bearer Token")
        self.bearer_auth_radio.setToolTip(
            "Require a bearer token for API access.\n"
            "Token is sent in the Authorization header with each request."
        )
        self.auth_type_button_group.addButton(self.bearer_auth_radio, 2)
        auth_type_layout.addWidget(self.bearer_auth_radio)

        auth_type_layout.addStretch()
        self.auth_type_button_group.buttonClicked.connect(self._update_auth_visibility)

        auth_layout.addLayout(auth_type_layout)

        # Basic Auth Fields
        self.basic_auth_widget = QWidget()
        basic_layout = QFormLayout(self.basic_auth_widget)
        basic_layout.setContentsMargins(0, 0, 0, 0)

        username_label = QLabel("Username:")
        username_label.setToolTip("Username required for API authentication.")
        self.basic_username_input = QLineEdit()
        self.basic_username_input.setPlaceholderText("Username")
        basic_layout.addRow(username_label, self.basic_username_input)

        password_label = QLabel("Password:")
        password_label.setToolTip("Password required for API authentication.")
        self.basic_password_input = QLineEdit()
        self.basic_password_input.setPlaceholderText("Password")
        self.basic_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        basic_layout.addRow(password_label, self.basic_password_input)

        auth_layout.addWidget(self.basic_auth_widget)

        # Bearer Token Fields
        self.bearer_auth_widget = QWidget()
        bearer_layout = QFormLayout(self.bearer_auth_widget)
        bearer_layout.setContentsMargins(0, 0, 0, 0)

        token_label = QLabel("Token:")
        token_label.setToolTip(
            "Secret token required for API authentication.\n"
            "This token should be kept secure and sent in the Authorization header."
        )
        self.bearer_token_input = QLineEdit()
        self.bearer_token_input.setPlaceholderText("Enter bearer token")
        self.bearer_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        bearer_layout.addRow(token_label, self.bearer_token_input)

        auth_layout.addWidget(self.bearer_auth_widget)

        layout.addWidget(auth_group)
        layout.addStretch()

        # Initially show/hide based on default selection
        self._update_auth_visibility()

    def _update_auth_visibility(self) -> None:
        """Update visibility of auth fields based on selected radio button."""
        self.basic_auth_widget.setVisible(self.basic_auth_radio.isChecked())
        self.bearer_auth_widget.setVisible(self.bearer_auth_radio.isChecked())

    def set_values(
        self, server_settings: APIServerSettings, auth_settings: APIAuthSettings | None = None
    ) -> None:
        """Set widget values from settings.

        Args:
            server_settings (APIServerSettings): APIServerSettings instance to load values from.
            auth_settings (APIAuthSettings | None): APIAuthSettings instance to load values from.
        """
        # Server settings
        self.host_input.setText(server_settings.host)
        self.port_input.setValue(server_settings.port)
        self.workers_input.setValue(server_settings.workers)

        # Convert list to JSON string for display
        cors_text = json.dumps(server_settings.cors_allow_origins, indent=2)
        self.cors_input.setPlainText(cors_text)

        self.memory_monitoring_input.setChecked(server_settings.enable_memory_monitoring)
        self.auto_trim_input.setChecked(server_settings.auto_trim_memory)
        self.web_icon_mod_input.setText(server_settings.web_icon_mod)

        # Auth settings
        if auth_settings:
            auth_type = auth_settings.auth_type or "null"
            if auth_type == "basic":
                self.basic_auth_radio.setChecked(True)
            elif auth_type == "bearer":
                self.bearer_auth_radio.setChecked(True)
            else:
                self.no_auth_radio.setChecked(True)

            # Parse and set credentials based on type
            if auth_settings.auth_token:
                if auth_type == "basic":
                    # Basic auth token format: "username:password"
                    if ":" in auth_settings.auth_token:
                        username, password = auth_settings.auth_token.split(":", 1)
                        self.basic_username_input.setText(username)
                        self.basic_password_input.setText(password)
                    else:
                        self.basic_username_input.setText(auth_settings.auth_token)
                elif auth_type == "bearer":
                    self.bearer_token_input.setText(auth_settings.auth_token)

            self._update_auth_visibility()

    def get_server_values(self) -> APIServerSettings:
        """Get current server values from widgets.

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
            web_icon_mod=self.web_icon_mod_input.text() or "vanilla",
        )

    def set_config_level(self, level: ConfigLevel) -> None:
        """Show or hide fields based on the configuration level.

        Args:
            level (ConfigLevel): The configuration level to set.
        """
        # Advanced widgets are visible at advanced and developer levels
        for widget in self._advanced_widgets:
            widget.setVisible(level.is_at_least(ConfigLevel.ADVANCED))

    def get_auth_values(self) -> APIAuthSettings:
        """Get current auth values from widgets.

        Returns:
            APIAuthSettings: APIAuthSettings instance with current values from widgets
        """
        # Determine auth type from radio buttons
        if self.basic_auth_radio.isChecked():
            auth_type = "basic"
        elif self.bearer_auth_radio.isChecked():
            auth_type = "bearer"
        else:
            auth_type = "null"

        # Build auth token based on type
        auth_token = None
        if auth_type == "basic":
            username = self.basic_username_input.text().strip()
            password = self.basic_password_input.text().strip()
            if username or password:
                auth_token = f"{username}:{password}"
        elif auth_type == "bearer":
            token = self.bearer_token_input.text().strip()
            if token:
                auth_token = token

        # If token is None but auth_type is set, reset auth_type to None
        if auth_token is None:
            auth_type = "null"

        return APIAuthSettings(
            auth_type=None if auth_type == "null" else AuthType(auth_type),
            auth_token=auth_token,
        )
