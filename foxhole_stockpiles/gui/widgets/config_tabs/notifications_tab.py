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
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t

# Available events for notification (id, translation_key_suffix)
AVAILABLE_EVENTS = [
    ("stockpile.scanned", "stockpile_scanned", "stockpile_scanned_desc"),
    ("stockpile.scan_failed", "scan_failed", "scan_failed_desc"),
    ("stockpile.scan_started", "scan_started", "scan_started_desc"),
    ("server.started", "server_started", "server_started_desc"),
    ("server.stopped", "server_stopped", "server_stopped_desc"),
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
        self.setMinimumWidth(650)

        layout = QVBoxLayout(self)

        # Basic settings
        self.basic_group = QGroupBox()
        basic_layout = QFormLayout()
        self.basic_group.setLayout(basic_layout)

        self.name_label = QLabel()
        self.name_input = QLineEdit()
        basic_layout.addRow(self.name_label, self.name_input)

        self.webhook_label = QLabel()
        self.webhook_input = QLineEdit()
        basic_layout.addRow(self.webhook_label, self.webhook_input)

        self.username_label = QLabel()
        self.username_input = QLineEdit()
        basic_layout.addRow(self.username_label, self.username_input)

        layout.addWidget(self.basic_group)

        # Events
        self.events_group = QGroupBox()
        self.events_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        events_outer_layout = QVBoxLayout()
        self.events_group.setLayout(events_outer_layout)

        self.events_desc = QLabel()
        self.events_desc.setStyleSheet("QLabel { color: gray; margin-bottom: 5px; }")
        events_outer_layout.addWidget(self.events_desc)

        # Grid layout for checkboxes (2 columns)
        events_grid = QGridLayout()
        events_grid.setColumnStretch(0, 1)
        events_grid.setColumnStretch(1, 1)

        self.event_checkboxes: dict[str, QCheckBox] = {}
        for i, (event_id, _name_key, _desc_key) in enumerate(AVAILABLE_EVENTS):
            checkbox = QCheckBox()
            self.event_checkboxes[event_id] = checkbox
            row = i // 2
            col = i % 2
            events_grid.addWidget(checkbox, row, col)

        events_outer_layout.addLayout(events_grid)

        layout.addWidget(self.events_group)

        # Message templates
        self.templates_group = QGroupBox()
        self.templates_layout = QFormLayout()
        self.templates_group.setLayout(self.templates_layout)

        self.templates_desc = QLabel()
        self.templates_desc.setStyleSheet("QLabel { color: gray; margin-bottom: 5px; }")
        self.templates_desc.setWordWrap(True)
        self.templates_layout.addRow(self.templates_desc)

        self.template_inputs: dict[str, QLineEdit] = {}
        self.template_labels: dict[str, QLabel] = {}
        for event_id, _name_key, _ in AVAILABLE_EVENTS:
            label = QLabel()
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(DEFAULT_TEMPLATES.get(event_id, ""))
            self.template_inputs[event_id] = line_edit
            self.template_labels[event_id] = label
            self.templates_layout.addRow(label, line_edit)

        layout.addWidget(self.templates_group)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Apply translations
        self.retranslate()

        # Connect to language change signal with cleanup
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)
        self.destroyed.connect(lambda: off_language_changed(self._language_callback))

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event."""
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        # Window title
        if self.notifier:
            self.setWindowTitle(t("notifications_tab.notifier_dialog.title_edit"))
        else:
            self.setWindowTitle(t("notifications_tab.notifier_dialog.title_add"))

        # Basic settings
        self.basic_group.setTitle(t("notifications_tab.notifier_dialog.basic_settings"))
        self.name_label.setText(t("common.name") + ":")
        self.name_input.setPlaceholderText(t("notifications_tab.notifier_dialog.name_placeholder"))
        self.name_input.setToolTip(t("notifications_tab.notifier_dialog.name_tooltip"))
        self.webhook_label.setText(t("notifications_tab.notifier_dialog.webhook_url"))
        self.webhook_input.setPlaceholderText(
            t("notifications_tab.notifier_dialog.webhook_placeholder")
        )
        self.webhook_input.setToolTip(t("notifications_tab.notifier_dialog.webhook_tooltip"))
        self.username_label.setText(t("notifications_tab.notifier_dialog.username") + ":")
        self.username_input.setPlaceholderText(
            t("notifications_tab.notifier_dialog.username_placeholder")
        )
        self.username_input.setToolTip(t("notifications_tab.notifier_dialog.username_tooltip"))

        # Events
        self.events_group.setTitle(t("notifications_tab.notifier_dialog.events_group"))
        self.events_desc.setText(t("notifications_tab.notifier_dialog.events_description"))

        # Update event checkboxes
        for event_id, name_key, desc_key in AVAILABLE_EVENTS:
            if event_id in self.event_checkboxes:
                self.event_checkboxes[event_id].setText(t(f"notifications_tab.events.{name_key}"))
                self.event_checkboxes[event_id].setToolTip(
                    t(f"notifications_tab.events.{desc_key}")
                )

        # Templates
        self.templates_group.setTitle(t("notifications_tab.notifier_dialog.templates_group"))
        self.templates_desc.setText(t("notifications_tab.notifier_dialog.templates_description"))

        # Update template labels
        for event_id, name_key, _ in AVAILABLE_EVENTS:
            if event_id in self.template_labels:
                event_name = t(f"notifications_tab.events.{name_key}")
                self.template_labels[event_id].setText(f"{event_name}:")
                self.template_inputs[event_id].setToolTip(
                    t("notifications_tab.notifier_dialog.templates_description")
                )

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
            QMessageBox.warning(
                self,
                t("common.validation_error"),
                t("notifications_tab.notifier_dialog.webhook_required"),
            )
            self.webhook_input.setFocus()
            return

        if not webhook.startswith("https://discord.com/api/webhooks/"):
            QMessageBox.warning(
                self,
                t("common.validation_error"),
                t("notifications_tab.notifier_dialog.webhook_invalid"),
            )
            self.webhook_input.setFocus()
            return

        # Check at least one event is selected
        selected_events = [
            event_id for event_id, checkbox in self.event_checkboxes.items() if checkbox.isChecked()
        ]
        if not selected_events:
            QMessageBox.warning(
                self,
                t("common.validation_error"),
                t("notifications_tab.notifier_dialog.event_required"),
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
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("QLabel { color: gray; margin-bottom: 10px; }")
        layout.addWidget(self.description_label)

        # Enable checkbox
        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_checkbox)

        # Notifiers group
        self.notifiers_group = QGroupBox()
        notifiers_layout = QVBoxLayout()
        self.notifiers_group.setLayout(notifiers_layout)

        # List widget
        self.notifiers_list = QListWidget()
        self.notifiers_list.setMinimumHeight(150)
        self.notifiers_list.itemDoubleClicked.connect(self._on_edit_clicked)
        notifiers_layout.addWidget(self.notifiers_list)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.add_button = QPushButton()
        self.add_button.clicked.connect(self._on_add_clicked)
        buttons_layout.addWidget(self.add_button)

        self.edit_button = QPushButton()
        self.edit_button.clicked.connect(self._on_edit_clicked)
        buttons_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton()
        self.remove_button.clicked.connect(self._on_remove_clicked)
        buttons_layout.addWidget(self.remove_button)

        buttons_layout.addStretch()
        notifiers_layout.addLayout(buttons_layout)

        layout.addWidget(self.notifiers_group)

        layout.addStretch()

        # Apply translations
        self.retranslate()

        # Initial state
        self._update_buttons_state()

        # Connect to language change signal with cleanup
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)
        self.destroyed.connect(lambda: off_language_changed(self._language_callback))

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event."""
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        self.description_label.setText(t("notifications_tab.description"))
        self.enabled_checkbox.setText(t("notifications_tab.enable_notifications"))
        self.enabled_checkbox.setToolTip(t("notifications_tab.enable_tooltip"))
        self.notifiers_group.setTitle(t("notifications_tab.notifiers_group"))

        self.add_button.setText(t("common.add"))
        self.edit_button.setText(t("common.edit"))
        self.remove_button.setText(t("common.remove"))

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
        message = t("notifications_tab.remove_notifier_message").replace("{name}", notifier.name)
        reply = QMessageBox.question(
            self,
            t("notifications_tab.remove_notifier_title"),
            message,
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
