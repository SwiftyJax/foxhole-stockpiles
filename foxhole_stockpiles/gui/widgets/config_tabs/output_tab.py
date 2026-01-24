"""Output settings tab."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.output import (
    ConsoleHandlerSettings,
    FileHandlerSettings,
    JsonFormatSettings,
    OutputHandlerConfig,
    OutputSettings,
    ReturnHandlerSettings,
    WebhookHandlerSettings,
)
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_handler_type import OutputHandlerType


class OutputHandlerDialog(QDialog):
    """Dialog for adding or editing an output handler."""

    def __init__(
        self,
        parent: QWidget | None = None,
        handler_config: OutputHandlerConfig | None = None,
    ) -> None:
        """Initialize the output handler dialog.

        Args:
            parent: Parent widget.
            handler_config: Existing handler config to edit, or None for new handler.
        """
        super().__init__(parent)
        self.handler_config = handler_config
        self.init_ui()
        if handler_config:
            self.load_handler(handler_config)

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Edit Handler" if self.handler_config else "Add Handler")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        basic_group.setLayout(basic_layout)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., File Backup")
        self.name_input.setToolTip("A friendly name to identify this output handler")
        basic_layout.addRow("Name:", self.name_input)

        handler_type_label = QLabel("Handler Type:")
        handler_type_label.setToolTip(
            "Where to send scan results:\n\n"
            "• return - Return data to caller (API mode)\n"
            "• file - Save to a JSON file\n"
            "• webhook - POST to a webhook URL\n"
            "• console - Print to console output"
        )
        self.handler_type_input = QComboBox()
        self.handler_type_input.addItems(["return", "file", "webhook", "console"])
        self.handler_type_input.currentTextChanged.connect(self._on_handler_type_changed)
        basic_layout.addRow(handler_type_label, self.handler_type_input)

        layout.addWidget(basic_group)

        # File Settings Group
        self.file_group = QGroupBox("File Output Settings")
        file_layout = QFormLayout()
        self.file_group.setLayout(file_layout)

        file_path_label = QLabel("File Path:")
        file_path_label.setToolTip(
            "Path where scan results will be saved.\n\n"
            "Supported placeholders:\n"
            "  {timestamp} - Full timestamp (YYYY-MM-DD_HH-MM-SS)\n"
            "  {year}, {month}, {day} - Date components\n"
            "  {hour}, {minute}, {second} - Time components\n"
            "  {stockpile_type} - Type (Seaport, Storage Depot, etc.)\n"
            "  {stockpile_name} - Name of the stockpile\n"
            "  {resolution} - Screen resolution (e.g., 1920x1080)\n\n"
            "Example: {timestamp}_{stockpile_type}_{stockpile_name}_{resolution}.json"
        )
        file_path_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText(
            "{timestamp}_{stockpile_type}_{stockpile_name}_{resolution}.json"
        )
        file_browse = QPushButton("Browse...")
        file_browse.clicked.connect(self._browse_file)
        file_path_layout.addWidget(self.file_path_input)
        file_path_layout.addWidget(file_browse)
        file_layout.addRow(file_path_label, file_path_layout)

        layout.addWidget(self.file_group)

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
        self.webhook_auth_type_input.currentTextChanged.connect(self._on_webhook_auth_changed)
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

        layout.addWidget(self.webhook_group)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Initially show/hide based on handler type and auth type
        self._on_handler_type_changed()
        self._on_webhook_auth_changed()

    def _on_handler_type_changed(self) -> None:
        """Handle handler type change to show/hide relevant sections."""
        handler_type = self.handler_type_input.currentText()
        self.file_group.setVisible(handler_type == "file")
        self.webhook_group.setVisible(handler_type == "webhook")

    def _on_webhook_auth_changed(self) -> None:
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

    def _browse_file(self) -> None:
        """Open file dialog for output file path."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if filepath:
            self.file_path_input.setText(filepath)

    def load_handler(self, handler_config: OutputHandlerConfig) -> None:
        """Load handler config settings into the dialog.

        Args:
            handler_config: Handler config to load.
        """
        self.name_input.setText(handler_config.name)
        handler = handler_config.handler
        self.handler_type_input.setCurrentText(handler.type)

        if isinstance(handler, FileHandlerSettings):
            self.file_path_input.setText(handler.path)
        elif isinstance(handler, WebhookHandlerSettings):
            self.webhook_url_input.setText(handler.url or "")
            self.webhook_auth_type_input.setCurrentText(handler.auth_type or "null")
            self.webhook_token_input.setText(handler.token or "")
            self.webhook_client_auth_input.setText(handler.client_auth_header or "")

        self._on_handler_type_changed()
        self._on_webhook_auth_changed()

    def _validate_and_accept(self) -> None:
        """Validate input and accept dialog if valid."""
        handler_type = self.handler_type_input.currentText()

        if handler_type == "file":
            path = self.file_path_input.text().strip()
            if not path:
                QMessageBox.warning(self, "Validation Error", "File path is required.")
                self.file_path_input.setFocus()
                return

        elif handler_type == "webhook":
            url = self.webhook_url_input.text().strip()
            if not url:
                QMessageBox.warning(self, "Validation Error", "Webhook URL is required.")
                self.webhook_url_input.setFocus()
                return

        self.accept()

    def get_handler_config(self) -> OutputHandlerConfig:
        """Get handler config from dialog input.

        Returns:
            OutputHandlerConfig with current values.
        """
        handler_type = OutputHandlerType(self.handler_type_input.currentText())
        name = self.name_input.text().strip()

        # Create appropriate handler settings based on type
        handler_settings: (
            ReturnHandlerSettings
            | FileHandlerSettings
            | WebhookHandlerSettings
            | ConsoleHandlerSettings
        )
        if handler_type == OutputHandlerType.FILE:
            handler_settings = FileHandlerSettings(
                path=self.file_path_input.text() or "output.json"
            )
            if not name:
                name = "File Output"
        elif handler_type == OutputHandlerType.WEBHOOK:
            webhook_auth_type_str = self.webhook_auth_type_input.currentText()
            webhook_auth_type: AuthType | None = (
                None if webhook_auth_type_str == "null" else AuthType(webhook_auth_type_str)
            )
            handler_settings = WebhookHandlerSettings(
                url=self.webhook_url_input.text() or "https://example.com/webhook",
                auth_type=webhook_auth_type,
                token=self.webhook_token_input.text() or None,
                client_auth_header=self.webhook_client_auth_input.text() or None,
            )
            if not name:
                name = "Webhook"
        elif handler_type == OutputHandlerType.CONSOLE:
            handler_settings = ConsoleHandlerSettings()
            if not name:
                name = "Console"
        else:  # RETURN
            handler_settings = ReturnHandlerSettings()
            if not name:
                name = "API Response"

        return OutputHandlerConfig(
            name=name,
            format=JsonFormatSettings(),
            handler=handler_settings,
        )


class OutputTab(QWidget):
    """Tab for Output configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Output tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self._handlers: list[OutputHandlerConfig] = []
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Description
        description = QLabel(
            "Configure output handlers for scan results.\n"
            "You can add multiple handlers to send results to different destinations."
        )
        description.setWordWrap(True)
        description.setStyleSheet("QLabel { color: gray; margin-bottom: 10px; }")
        layout.addWidget(description)

        # Handlers group
        handlers_group = QGroupBox("Output Handlers")
        handlers_layout = QVBoxLayout()
        handlers_group.setLayout(handlers_layout)

        # List widget
        self.handlers_list = QListWidget()
        self.handlers_list.setMinimumHeight(150)
        self.handlers_list.itemDoubleClicked.connect(self._on_edit_clicked)
        self.handlers_list.itemSelectionChanged.connect(self._update_buttons_state)
        handlers_layout.addWidget(self.handlers_list)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.add_button = QPushButton("Add")
        self.add_button.setToolTip("Add a new output handler")
        self.add_button.clicked.connect(self._on_add_clicked)
        buttons_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.setToolTip("Edit the selected handler")
        self.edit_button.clicked.connect(self._on_edit_clicked)
        buttons_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setToolTip("Remove the selected handler")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        buttons_layout.addWidget(self.remove_button)

        buttons_layout.addStretch()
        handlers_layout.addLayout(buttons_layout)

        layout.addWidget(handlers_group)
        layout.addStretch()

        # Initial state
        self._update_buttons_state()

    def _update_buttons_state(self) -> None:
        """Update button enabled states based on selection."""
        has_selection = self.handlers_list.currentRow() >= 0
        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def _update_list(self) -> None:
        """Update the handlers list widget."""
        self.handlers_list.clear()
        for handler_config in self._handlers:
            handler = handler_config.handler
            handler_type = handler.type
            item_text = f"{handler_config.name} ({handler_type})"

            # Add extra info based on type
            if isinstance(handler, FileHandlerSettings):
                item_text = f"{handler_config.name} - {handler.path}"
            elif isinstance(handler, WebhookHandlerSettings):
                url = handler.url or ""
                truncated_url = url[:40] + "..." if len(url) > 40 else url
                item_text = f"{handler_config.name} - {truncated_url}"

            item = QListWidgetItem(item_text)
            item.setToolTip(f"Type: {handler_type}")
            self.handlers_list.addItem(item)
        self._update_buttons_state()

    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        dialog = OutputHandlerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            handler_config = dialog.get_handler_config()
            self._handlers.append(handler_config)
            self._update_list()
            # Select the new item
            self.handlers_list.setCurrentRow(len(self._handlers) - 1)

    def _on_edit_clicked(self) -> None:
        """Handle edit button click."""
        row = self.handlers_list.currentRow()
        if row < 0:
            return

        handler_config = self._handlers[row]
        dialog = OutputHandlerDialog(self, handler_config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._handlers[row] = dialog.get_handler_config()
            self._update_list()
            self.handlers_list.setCurrentRow(row)

    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        row = self.handlers_list.currentRow()
        if row < 0:
            return

        handler_config = self._handlers[row]
        reply = QMessageBox.question(
            self,
            "Remove Handler",
            f"Are you sure you want to remove '{handler_config.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self._handlers[row]
            self._update_list()

    def set_values(self, settings: OutputSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (OutputSettings): OutputSettings instance to load values from.
        """
        self._handlers = list(settings.handlers)
        self._update_list()

    def get_values(self) -> OutputSettings:
        """Get current values from widgets.

        Returns:
            OutputSettings: OutputSettings instance with current values from widgets
        """
        return OutputSettings(handlers=list(self._handlers))
