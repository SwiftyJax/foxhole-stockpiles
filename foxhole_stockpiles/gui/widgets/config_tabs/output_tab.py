"""Output settings tab."""

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
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.output import (
    FileOutputSettings,
    OutputSettings,
    WebhookOutputSettings,
)
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat


class OutputTab(QWidget):
    """Tab for Output configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Output tab.

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

        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)

        # Format
        format_label = QLabel("Format:")
        format_label.setToolTip(
            "Output format for scan results.\n\n"
            "Determines how the detected stockpile data is structured."
        )
        self.format_input = QComboBox()
        self.format_input.addItems(["json"])
        form_layout.addRow(format_label, self.format_input)

        # Destination
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
        self.destination_input.currentTextChanged.connect(self.on_destination_changed)
        form_layout.addRow(destination_label, self.destination_input)

        # File Settings Group
        self.file_group = QGroupBox("File Output Settings")
        file_layout = QFormLayout()
        self.file_group.setLayout(file_layout)

        file_path_label = QLabel("File Path:")
        file_path_label.setToolTip(
            "Path where scan results will be saved.\n\n"
            "Can be absolute or relative path.\n"
            "File will be created or overwritten with each scan."
        )
        file_path_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("output.json")
        file_browse = QPushButton("Browse...")
        file_browse.clicked.connect(self.browse_file)
        file_path_layout.addWidget(self.file_path_input)
        file_path_layout.addWidget(file_browse)
        file_layout.addRow(file_path_label, file_path_layout)

        main_layout.addWidget(self.file_group)

        # Webhook Settings Group
        self.webhook_group = QGroupBox("Webhook Output Settings")
        webhook_layout = QFormLayout()
        self.webhook_group.setLayout(webhook_layout)

        webhook_url_label = QLabel("Webhook URL:")
        webhook_url_label.setToolTip(
            "URL to POST scan results to.\n\n"
            "Results will be sent as JSON in the request body.\n"
            "The webhook should accept POST requests with application/json content type."
        )
        self.webhook_url_input = QLineEdit()
        self.webhook_url_input.setPlaceholderText("https://example.com/webhook")
        webhook_layout.addRow(webhook_url_label, self.webhook_url_input)

        auth_type_label = QLabel("Auth Type:")
        auth_type_label.setToolTip(
            "Authentication type for webhook requests:\n\n"
            "• null - No authentication\n"
            "• basic - HTTP Basic Auth (username:password)\n"
            "• bearer - Bearer token in Authorization header\n"
            "• forward - Forward client's Authorization header to webhook"
        )
        self.webhook_auth_type_input = QComboBox()
        self.webhook_auth_type_input.addItems(["null", "basic", "bearer", "forward"])
        self.webhook_auth_type_input.currentTextChanged.connect(self.on_webhook_auth_changed)
        webhook_layout.addRow(auth_type_label, self.webhook_auth_type_input)

        self.auth_token_label = QLabel("Auth Token:")
        self.auth_token_label.setToolTip(
            "Authentication credentials for webhook.\n\n"
            "• For basic auth: use format 'username:password'\n"
            "• For bearer auth: just the token value\n\n"
            "Required when auth type is 'basic' or 'bearer'."
        )
        self.webhook_token_input = QLineEdit()
        self.webhook_token_input.setPlaceholderText("Token or credentials")
        self.webhook_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        webhook_layout.addRow(self.auth_token_label, self.webhook_token_input)

        self.client_auth_label = QLabel("Client Auth Header:")
        self.client_auth_label.setToolTip(
            "Name of the Authorization header to forward from API client to webhook.\n\n"
            "Useful when the webhook needs to know who initiated the scan.\n\n"
            "Required when auth type is 'forward'."
        )
        self.webhook_client_auth_input = QLineEdit()
        self.webhook_client_auth_input.setPlaceholderText("e.g., Authorization")
        webhook_layout.addRow(self.client_auth_label, self.webhook_client_auth_input)

        main_layout.addWidget(self.webhook_group)

        # Initially show/hide based on destination and auth type
        self.on_destination_changed()
        self.on_webhook_auth_changed()

    def on_destination_changed(self) -> None:
        """Handle destination change to show/hide relevant sections."""
        destination = self.destination_input.currentText()
        self.file_group.setVisible(destination == "file")
        self.webhook_group.setVisible(destination == "webhook")

    def on_webhook_auth_changed(self) -> None:
        """Handle webhook auth type change to show/hide relevant fields."""
        auth_type = self.webhook_auth_type_input.currentText()

        # Show token fields for basic/bearer, hide for forward/null
        show_token = auth_type in ("basic", "bearer")
        self.auth_token_label.setVisible(show_token)
        self.webhook_token_input.setVisible(show_token)

        # Show client auth header field only for forward
        show_client_auth = auth_type == "forward"
        self.client_auth_label.setVisible(show_client_auth)
        self.webhook_client_auth_input.setVisible(show_client_auth)

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

    def set_values(self, settings: OutputSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (OutputSettings): OutputSettings instance to load values from.
        """
        self.format_input.setCurrentText(settings.format)
        self.destination_input.setCurrentText(settings.destination)

        # File settings
        if settings.file:
            self.file_path_input.setText(str(settings.file.path))

        # Webhook settings
        if settings.webhook:
            self.webhook_url_input.setText(settings.webhook.url or "")
            self.webhook_auth_type_input.setCurrentText(settings.webhook.auth_type or "null")
            self.webhook_token_input.setText(settings.webhook.token or "")
            self.webhook_client_auth_input.setText(settings.webhook.client_auth_header or "")

    def get_values(self) -> OutputSettings:
        """Get current values from widgets.

        Returns:
            OutputSettings: OutputSettings instance with current values from widgets.
        """
        webhook_auth_type_str = self.webhook_auth_type_input.currentText()
        webhook_auth_type: AuthType | None = (
            None if webhook_auth_type_str == "null" else AuthType(webhook_auth_type_str)
        )

        return OutputSettings(
            format=OutputFormat(self.format_input.currentText()),
            destination=OutputDestination(self.destination_input.currentText()),
            file=FileOutputSettings(path=self.file_path_input.text()),
            webhook=WebhookOutputSettings(
                url=self.webhook_url_input.text() or None,
                auth_type=webhook_auth_type,
                token=self.webhook_token_input.text() or None,
                client_auth_header=self.webhook_client_auth_input.text() or None,
            ),
        )
