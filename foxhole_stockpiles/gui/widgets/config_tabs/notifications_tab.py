"""Notifications settings tab."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.notifications import (
    DEFAULT_TEMPLATES,
    DiscordNotifierSettings,
    NotificationsSettings,
)
from foxhole_stockpiles.enums.notifier_type import NotifierType

# Available events for notification
AVAILABLE_EVENTS = [
    ("stockpile.scanned", "Stockpile Scanned", "When a stockpile scan completes successfully"),
    ("stockpile.scan_failed", "Scan Failed", "When a stockpile scan fails"),
    ("stockpile.scan_started", "Scan Started", "When a stockpile scan begins"),
    ("server.started", "Server Started", "When the API server starts"),
    ("server.stopped", "Server Stopped", "When the API server stops"),
]


class NotifierDialog(QDialog):
    """Dialog for adding or editing a Discord notifier."""

    def __init__(
        self,
        parent: QWidget | None = None,
        notifier: DiscordNotifierSettings | None = None,
    ) -> None:
        """Initialize the notifier dialog.

        Args:
            parent: Parent widget.
            notifier: Existing notifier to edit, or None for new notifier.
        """
        super().__init__(parent)
        self.notifier = notifier
        self.init_ui()
        if notifier:
            self.load_notifier(notifier)

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Edit Notifier" if self.notifier else "Add Notifier")
        self.setMinimumWidth(650)

        layout = QVBoxLayout(self)

        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        basic_group.setLayout(basic_layout)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Main Discord")
        self.name_input.setToolTip("A friendly name to identify this notifier")
        basic_layout.addRow("Name:", self.name_input)

        self.webhook_input = QLineEdit()
        self.webhook_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        self.webhook_input.setToolTip("Discord webhook URL for sending notifications")
        basic_layout.addRow("Webhook URL:", self.webhook_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Foxhole Stockpiles")
        self.username_input.setToolTip("Custom username shown for webhook messages")
        basic_layout.addRow("Username:", self.username_input)

        layout.addWidget(basic_group)

        # Events
        events_group = QGroupBox("Events to Notify")
        events_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        events_outer_layout = QVBoxLayout()
        events_group.setLayout(events_outer_layout)

        events_desc = QLabel("Select which events should trigger notifications:")
        events_desc.setStyleSheet("QLabel { color: gray; margin-bottom: 5px; }")
        events_outer_layout.addWidget(events_desc)

        # Grid layout for checkboxes (2 columns)
        events_grid = QGridLayout()
        events_grid.setColumnStretch(0, 1)
        events_grid.setColumnStretch(1, 1)

        self.event_checkboxes: dict[str, QCheckBox] = {}
        for i, (event_id, event_name, event_desc) in enumerate(AVAILABLE_EVENTS):
            checkbox = QCheckBox(event_name)
            checkbox.setToolTip(event_desc)
            self.event_checkboxes[event_id] = checkbox
            row = i // 2
            col = i % 2
            events_grid.addWidget(checkbox, row, col)

        events_outer_layout.addLayout(events_grid)

        layout.addWidget(events_group)

        # Message templates
        templates_group = QGroupBox("Custom Message Templates (Optional)")
        templates_layout = QFormLayout()
        templates_group.setLayout(templates_layout)

        templates_desc = QLabel(
            "Override default message templates. Leave blank to use defaults.\n"
            "Placeholders: STOCKPILE_NAME, STOCKPILE_TYPE, SHARD, TIME, ITEM_COUNT,\n"
            "MATCHED_ITEMS, UNMATCHED_ITEMS, AVG_CONFIDENCE, DURATION, RESOLUTION, ERROR"
        )
        templates_desc.setStyleSheet("QLabel { color: gray; margin-bottom: 5px; }")
        templates_desc.setWordWrap(True)
        templates_layout.addRow(templates_desc)

        self.template_inputs: dict[str, QLineEdit] = {}
        for event_id, event_name, _ in AVAILABLE_EVENTS:
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(DEFAULT_TEMPLATES.get(event_id, ""))
            line_edit.setToolTip(f"Custom template for {event_name} event")
            self.template_inputs[event_id] = line_edit
            templates_layout.addRow(f"{event_name}:", line_edit)

        layout.addWidget(templates_group)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_notifier(self, notifier: DiscordNotifierSettings) -> None:
        """Load notifier settings into the dialog.

        Args:
            notifier: Notifier settings to load.
        """
        self.name_input.setText(notifier.name)
        self.webhook_input.setText(notifier.webhook_url)
        self.username_input.setText(notifier.username or "")

        for event_id, checkbox in self.event_checkboxes.items():
            checkbox.setChecked(event_id in notifier.events)

        for event_id, line_edit in self.template_inputs.items():
            template = notifier.message_templates.get(event_id, "")
            line_edit.setText(template)

    def validate_and_accept(self) -> None:
        """Validate input and accept dialog if valid."""
        webhook = self.webhook_input.text().strip()
        if not webhook:
            QMessageBox.warning(self, "Validation Error", "Webhook URL is required.")
            self.webhook_input.setFocus()
            return

        if not webhook.startswith("https://discord.com/api/webhooks/"):
            QMessageBox.warning(
                self,
                "Validation Error",
                "Webhook URL must start with 'https://discord.com/api/webhooks/'",
            )
            self.webhook_input.setFocus()
            return

        # Check at least one event is selected
        selected_events = [
            event_id for event_id, checkbox in self.event_checkboxes.items() if checkbox.isChecked()
        ]
        if not selected_events:
            QMessageBox.warning(
                self, "Validation Error", "Please select at least one event to notify."
            )
            return

        self.accept()

    def get_notifier(self) -> DiscordNotifierSettings:
        """Get notifier settings from dialog input.

        Returns:
            DiscordNotifierSettings with current values.
        """
        events = [
            event_id for event_id, checkbox in self.event_checkboxes.items() if checkbox.isChecked()
        ]

        templates = {}
        for event_id, line_edit in self.template_inputs.items():
            text = line_edit.text().strip()
            if text:
                templates[event_id] = text

        name = self.name_input.text().strip() or "Discord"
        username = self.username_input.text().strip() or None

        return DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name=name,
            webhook_url=self.webhook_input.text().strip(),
            username=username,
            events=events,
            message_templates=templates,
        )


class NotificationsTab(QWidget):
    """Tab for configuring notification settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the notifications tab.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._notifiers: list[DiscordNotifierSettings] = []
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Description
        description = QLabel(
            "Configure Discord webhooks to receive notifications about stockpile scans\n"
            "and server events. You can add multiple notifiers with different settings."
        )
        description.setWordWrap(True)
        description.setStyleSheet("QLabel { color: gray; margin-bottom: 10px; }")
        layout.addWidget(description)

        # Enable checkbox
        self.enabled_checkbox = QCheckBox("Enable Notifications")
        self.enabled_checkbox.setToolTip("Master switch to enable or disable all notifications")
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_checkbox)

        # Notifiers group
        notifiers_group = QGroupBox("Discord Notifiers")
        notifiers_layout = QVBoxLayout()
        notifiers_group.setLayout(notifiers_layout)

        # List widget
        self.notifiers_list = QListWidget()
        self.notifiers_list.setMinimumHeight(150)
        self.notifiers_list.itemDoubleClicked.connect(self._on_edit_clicked)
        notifiers_layout.addWidget(self.notifiers_list)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.add_button = QPushButton("Add")
        self.add_button.setToolTip("Add a new Discord notifier")
        self.add_button.clicked.connect(self._on_add_clicked)
        buttons_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.setToolTip("Edit the selected notifier")
        self.edit_button.clicked.connect(self._on_edit_clicked)
        buttons_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setToolTip("Remove the selected notifier")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        buttons_layout.addWidget(self.remove_button)

        buttons_layout.addStretch()
        notifiers_layout.addLayout(buttons_layout)

        self.notifiers_group = notifiers_group
        layout.addWidget(notifiers_group)

        layout.addStretch()

        # Initial state
        self._update_buttons_state()

    def _on_enabled_changed(self) -> None:
        """Handle enabled checkbox state change."""
        self.notifiers_group.setEnabled(self.enabled_checkbox.isChecked())

    def _update_buttons_state(self) -> None:
        """Update button enabled states based on selection."""
        has_selection = self.notifiers_list.currentRow() >= 0
        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def _update_list(self) -> None:
        """Update the notifiers list widget."""
        self.notifiers_list.clear()
        for notifier in self._notifiers:
            events_str = ", ".join(notifier.events[:2])
            if len(notifier.events) > 2:
                events_str += f" (+{len(notifier.events) - 2} more)"
            item_text = f"{notifier.name} - {events_str}"
            item = QListWidgetItem(item_text)
            item.setToolTip(f"Webhook: {notifier.webhook_url[:50]}...")
            self.notifiers_list.addItem(item)
        self._update_buttons_state()

    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        dialog = NotifierDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            notifier = dialog.get_notifier()
            self._notifiers.append(notifier)
            self._update_list()
            # Select the new item
            self.notifiers_list.setCurrentRow(len(self._notifiers) - 1)

    def _on_edit_clicked(self) -> None:
        """Handle edit button click."""
        row = self.notifiers_list.currentRow()
        if row < 0:
            return

        notifier = self._notifiers[row]
        dialog = NotifierDialog(self, notifier)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._notifiers[row] = dialog.get_notifier()
            self._update_list()
            self.notifiers_list.setCurrentRow(row)

    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        row = self.notifiers_list.currentRow()
        if row < 0:
            return

        notifier = self._notifiers[row]
        reply = QMessageBox.question(
            self,
            "Remove Notifier",
            f"Are you sure you want to remove '{notifier.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self._notifiers[row]
            self._update_list()

    def set_values(self, settings: NotificationsSettings) -> None:
        """Set widget values from settings.

        Args:
            settings: Settings instance to load values from.
        """
        self.enabled_checkbox.setChecked(settings.enabled)
        self._notifiers = list(settings.notifiers)
        self._update_list()
        self._on_enabled_changed()

    def get_values(self) -> NotificationsSettings:
        """Get current values from widgets.

        Returns:
            NotificationsSettings with current values.
        """
        return NotificationsSettings(
            enabled=self.enabled_checkbox.isChecked(),
            notifiers=list(self._notifiers),
        )
