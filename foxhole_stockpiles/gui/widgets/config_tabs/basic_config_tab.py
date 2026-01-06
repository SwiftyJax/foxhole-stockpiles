"""Basic configuration tab for non-technical users."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.api import APIAuthSettings, APIServerSettings
from foxhole_stockpiles.core.settings.sections.output import (
    FileOutputSettings,
    OutputSettings,
    WebhookOutputSettings,
)
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat


class BasicConfigTab(QWidget):
    """Simplified configuration tab for basic users."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Basic Configuration tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        # Use scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        main_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

        # Server Settings Group
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        server_group.setLayout(server_layout)

        port_label = QLabel("Port:")
        port_label.setToolTip(
            "Port number the API server will listen on.\n\n"
            "Default: 8000. Change if port is already in use."
        )
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8000)
        server_layout.addRow(port_label, self.port_input)

        main_layout.addWidget(server_group)

        # Authentication Group
        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout()
        auth_group.setLayout(auth_layout)

        auth_type_label = QLabel("Auth Type:")
        auth_type_label.setToolTip(
            "Authentication for API access:\n\n"
            "• None - No authentication required\n"
            "• Basic - Require username and password"
        )
        self.auth_type_input = QComboBox()
        self.auth_type_input.addItems(["None", "Basic"])
        self.auth_type_input.currentTextChanged.connect(self.on_auth_changed)
        auth_layout.addRow(auth_type_label, self.auth_type_input)

        self.username_label = QLabel("Username:")
        self.username_label.setToolTip("Username for API authentication.")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        auth_layout.addRow(self.username_label, self.username_input)

        self.password_label = QLabel("Password:")
        self.password_label.setToolTip("Password for API authentication.")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow(self.password_label, self.password_input)

        main_layout.addWidget(auth_group)

        # Scanner Settings Group
        scanner_group = QGroupBox("Scanner Settings")
        scanner_layout = QFormLayout()
        scanner_group.setLayout(scanner_layout)

        db_label = QLabel("Database Path:")
        db_label.setToolTip(
            "Path to the template database file.\n\n"
            "Required for scanning stockpile screenshots.\n"
            "Use 'update-db' command to create this file first."
        )
        db_layout = QHBoxLayout()
        self.database_path_input = QLineEdit()
        self.database_path_input.setPlaceholderText("Path to database (.h5 file)")
        db_browse = QPushButton("Browse...")
        db_browse.clicked.connect(self.browse_database)
        db_layout.addWidget(self.database_path_input)
        db_layout.addWidget(db_browse)
        scanner_layout.addRow(db_label, db_layout)

        main_layout.addWidget(scanner_group)

        # Output Settings Group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()
        output_group.setLayout(output_layout)

        destination_label = QLabel("Destination:")
        destination_label.setToolTip(
            "Where to send scan results:\n\n"
            "• return - Return data to caller (API mode)\n"
            "• file - Save to a JSON file\n"
            "• webhook - POST to a webhook URL\n"
            "• console - Print to console output"
        )
        self.destination_input = QComboBox()
        self.destination_input.addItems(["return", "file", "webhook", "console"])
        self.destination_input.setCurrentText("console")  # Default to console for basic users
        self.destination_input.currentTextChanged.connect(self.on_destination_changed)
        output_layout.addRow(destination_label, self.destination_input)

        # File output
        self.file_group = QGroupBox("File Output")
        file_layout = QFormLayout()
        self.file_group.setLayout(file_layout)

        file_path_label = QLabel("File Path:")
        file_path_label.setToolTip("Path where scan results will be saved.")
        file_path_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("output.json")
        file_browse = QPushButton("Browse...")
        file_browse.clicked.connect(self.browse_file)
        file_path_layout.addWidget(self.file_path_input)
        file_path_layout.addWidget(file_browse)
        file_layout.addRow(file_path_label, file_path_layout)
        output_layout.addRow(self.file_group)

        # Webhook output
        self.webhook_group = QGroupBox("Webhook Output")
        webhook_layout = QFormLayout()
        self.webhook_group.setLayout(webhook_layout)

        webhook_url_label = QLabel("Webhook URL:")
        webhook_url_label.setToolTip("URL to POST scan results to.\n\nResults are sent as JSON.")
        self.webhook_url_input = QLineEdit()
        self.webhook_url_input.setPlaceholderText("https://example.com/webhook")
        webhook_layout.addRow(webhook_url_label, self.webhook_url_input)

        webhook_auth_type_label = QLabel("Webhook Auth:")
        webhook_auth_type_label.setToolTip(
            "Authentication for webhook access:\n\n"
            "• None - No authentication required\n"
            "• Basic - Require username and password"
        )
        self.webhook_auth_type_input = QComboBox()
        self.webhook_auth_type_input.addItems(["None", "Basic"])
        self.webhook_auth_type_input.currentTextChanged.connect(self.on_webhook_auth_changed)
        webhook_layout.addRow(webhook_auth_type_label, self.webhook_auth_type_input)

        self.webhook_username_label = QLabel("Webhook Username:")
        self.webhook_username_label.setToolTip("Username for webhook authentication.")
        self.webhook_username_input = QLineEdit()
        self.webhook_username_input.setPlaceholderText("Username")
        webhook_layout.addRow(self.webhook_username_label, self.webhook_username_input)

        self.webhook_password_label = QLabel("Webhook Password:")
        self.webhook_password_label.setToolTip("Password for webhook authentication.")
        self.webhook_password_input = QLineEdit()
        self.webhook_password_input.setPlaceholderText("Password")
        self.webhook_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        webhook_layout.addRow(self.webhook_password_label, self.webhook_password_input)

        output_layout.addRow(self.webhook_group)

        main_layout.addWidget(output_group)

        # Info label at bottom
        info_label = QLabel(
            "ℹ️ <b>Basic Configuration Mode:</b> This shows a reduced set of options "
            "for average users. "
            "Click <b>Show Advanced Settings</b> above to access all configuration options. "
            "<br><br>"
            "⚠️ <b>Warning:</b> Some advanced options are critical - misconfiguring "
            "them can break stockpile scanning completely."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "QLabel { "
            "background-color: #e3f2fd; "
            "color: #000000; "
            "padding: 12px; "
            "border: 1px solid #2196f3; "
            "border-radius: 4px; "
            "}"
        )
        main_layout.addWidget(info_label)

        # Initially show/hide based on defaults
        self.on_auth_changed()
        self.on_webhook_auth_changed()
        self.on_destination_changed()

        main_layout.addStretch()

    def on_auth_changed(self) -> None:
        """Handle authentication type change."""
        auth_enabled = self.auth_type_input.currentText() == "Basic"
        self.username_label.setVisible(auth_enabled)
        self.username_input.setVisible(auth_enabled)
        self.password_label.setVisible(auth_enabled)
        self.password_input.setVisible(auth_enabled)

    def on_webhook_auth_changed(self) -> None:
        """Handle webhook authentication type change."""
        webhook_auth_enabled = self.webhook_auth_type_input.currentText() == "Basic"
        self.webhook_username_label.setVisible(webhook_auth_enabled)
        self.webhook_username_input.setVisible(webhook_auth_enabled)
        self.webhook_password_label.setVisible(webhook_auth_enabled)
        self.webhook_password_input.setVisible(webhook_auth_enabled)

    def on_destination_changed(self) -> None:
        """Handle destination change to show/hide sections."""
        destination = self.destination_input.currentText()
        self.file_group.setVisible(destination == "file")
        self.webhook_group.setVisible(destination == "webhook")

    def browse_database(self) -> None:
        """Open file dialog for database path."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template Database",
            "",
            "HDF5 Files (*.h5);;All Files (*)",
        )
        if filepath:
            self.database_path_input.setText(filepath)

    def browse_file(self) -> None:
        """Open file dialog for output file path."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if filepath:
            self.file_path_input.setText(filepath)

    def set_values(
        self,
        api_server: APIServerSettings,
        api_auth: APIAuthSettings,
        scanner: ScannerSettings,
        output: OutputSettings,
    ) -> None:
        """Set widget values from settings.

        Args:
            api_server (APIServerSettings): API server settings
            api_auth (APIAuthSettings): API authentication settings
            scanner (ScannerSettings): Scanner settings
            output (OutputSettings): Output settings
        """
        # API Server
        self.port_input.setValue(api_server.port)

        # API Auth
        if api_auth.auth_type == "basic":
            self.auth_type_input.setCurrentText("Basic")
            if api_auth.auth_token and ":" in api_auth.auth_token:
                username, password = api_auth.auth_token.split(":", 1)
                self.username_input.setText(username)
                self.password_input.setText(password)
        else:
            self.auth_type_input.setCurrentText("None")

        # Scanner
        self.database_path_input.setText(
            str(scanner.database_path) if scanner.database_path else ""
        )

        # Output
        self.destination_input.setCurrentText(output.destination)
        if output.file:
            self.file_path_input.setText(str(output.file.path))
        if output.webhook:
            self.webhook_url_input.setText(output.webhook.url or "")
            # Webhook auth
            if output.webhook.auth_type == "basic":
                self.webhook_auth_type_input.setCurrentText("Basic")
                if output.webhook.token and ":" in output.webhook.token:
                    username, password = output.webhook.token.split(":", 1)
                    self.webhook_username_input.setText(username)
                    self.webhook_password_input.setText(password)
            else:
                self.webhook_auth_type_input.setCurrentText("None")

    def get_values(
        self,
    ) -> tuple[APIServerSettings, APIAuthSettings, ScannerSettings, OutputSettings]:
        """Get current values from widgets.

        Returns:
            tuple[APIServerSettings, APIAuthSettings, ScannerSettings, OutputSettings]: Tuple of
              (APIServerSettings, APIAuthSettings, ScannerSettings, OutputSettings)
        """
        # API Server - use defaults for other values
        api_server = APIServerSettings(port=self.port_input.value())

        # API Auth
        auth_type: AuthType | None = None
        auth_token = None
        if self.auth_type_input.currentText() == "Basic":
            auth_type = AuthType.BASIC
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            if username or password:
                auth_token = f"{username}:{password}"

        # Validation requires both auth_type and auth_token to be set or both to be None
        # If token is None but auth_type is set, reset auth_type to None
        if auth_token is None:
            auth_type = None

        api_auth = APIAuthSettings(auth_type=auth_type, auth_token=auth_token)

        # Scanner - use defaults for other values
        db_path_text = self.database_path_input.text()
        scanner = ScannerSettings(database_path=Path(db_path_text) if db_path_text else None)

        # Webhook auth
        webhook_auth_type: AuthType | None = None
        webhook_token = None
        if self.webhook_auth_type_input.currentText() == "Basic":
            webhook_auth_type = AuthType.BASIC
            username = self.webhook_username_input.text().strip()
            password = self.webhook_password_input.text().strip()
            if username or password:
                webhook_token = f"{username}:{password}"

        # Output
        output = OutputSettings(
            format=OutputFormat.JSON,
            destination=OutputDestination(self.destination_input.currentText()),
            file=FileOutputSettings(path=self.file_path_input.text()),
            webhook=WebhookOutputSettings(
                url=self.webhook_url_input.text() or None,
                auth_type=webhook_auth_type,
                token=webhook_token,
                client_auth_header=None,
            ),
        )

        return api_server, api_auth, scanner, output
