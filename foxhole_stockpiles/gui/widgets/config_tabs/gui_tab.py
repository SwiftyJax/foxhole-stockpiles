"""GUI settings tab."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.gui import GUISettings
from foxhole_stockpiles.enums.config_level import ConfigLevel
from foxhole_stockpiles.i18n import (
    get_available_languages,
    off_language_changed,
    on_language_changed,
    t,
)


class GUITab(QWidget):
    """Tab for GUI configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the GUI tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Configuration Level Group
        self.config_level_group = QGroupBox("Configuration Level")
        config_level_layout = QFormLayout()
        self.config_level_group.setLayout(config_level_layout)

        # Config Level Dropdown
        self.config_level_label = QLabel("Level:")
        self.config_level_label.setToolTip(
            "Controls which configuration options are visible in the GUI.\n\n"
            "Basic: Essential settings only (recommended for most users)\n"
            "Advanced: Additional tuning options for power users\n"
            "Developer: Full access including OCR/Template settings"
        )
        self.config_level_input = QComboBox()
        self.config_level_input.addItem("Basic", ConfigLevel.BASIC)
        self.config_level_input.addItem("Advanced", ConfigLevel.ADVANCED)
        self.config_level_input.addItem("Developer", ConfigLevel.DEVELOPER)
        self.config_level_input.currentIndexChanged.connect(self._update_warning_visibility)
        config_level_layout.addRow(self.config_level_label, self.config_level_input)

        # Warning label (shown for Advanced/Developer)
        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet(
            "QLabel { "
            "background-color: #fff3cd; "
            "color: #856404; "
            "padding: 10px; "
            "border: 1px solid #ffc107; "
            "border-radius: 4px; "
            "}"
        )
        config_level_layout.addRow(self.warning_label)

        layout.addWidget(self.config_level_group)

        # Window Behavior Group
        self.window_group = QGroupBox("Window Behavior")
        window_layout = QFormLayout()
        self.window_group.setLayout(window_layout)

        # Minimize to Tray
        self.minimize_label = QLabel("Minimize to Tray:")
        self.minimize_label.setToolTip(
            "When enabled, closing the window minimizes to system tray\n"
            "instead of quitting the application.\n\n"
            "The application will continue running in the background.\n"
            "Right-click the tray icon to access options or quit."
        )
        self.minimize_to_tray_input = QCheckBox("Minimize to tray on close")
        window_layout.addRow(self.minimize_label, self.minimize_to_tray_input)

        layout.addWidget(self.window_group)

        # Language Group
        self.language_group = QGroupBox("Language")
        language_layout = QFormLayout()
        self.language_group.setLayout(language_layout)

        self.language_label = QLabel("Language:")
        self.language_label.setToolTip("Select the language for the GUI.")
        self.language_input = QComboBox()
        # Populate with available languages
        for code, name in get_available_languages():
            self.language_input.addItem(name, code)
        language_layout.addRow(self.language_label, self.language_input)

        layout.addWidget(self.language_group)
        layout.addStretch()

        # Connect to language change events for retranslation
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)

        # Disconnect callback when widget is destroyed
        self.destroyed.connect(self._cleanup)

        # Initialize warning visibility
        self._update_warning_visibility()

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event.

        Args:
            _language: The new language code (unused).
        """
        self.retranslate()

    def _cleanup(self) -> None:
        """Clean up signal connections when widget is destroyed."""
        off_language_changed(self._language_callback)

    def _update_warning_visibility(self) -> None:
        """Update warning label visibility and text based on selected level."""
        level = self.config_level_input.currentData()

        if level == ConfigLevel.BASIC:
            self.warning_label.setVisible(False)
        elif level == ConfigLevel.ADVANCED:
            self.warning_label.setVisible(True)
            self.warning_label.setText(t("gui_tab.warning_advanced"))
            self.warning_label.setStyleSheet(
                "QLabel { "
                "background-color: #fff3cd; "
                "color: #856404; "
                "padding: 10px; "
                "border: 1px solid #ffc107; "
                "border-radius: 4px; "
                "}"
            )
        else:  # developer
            self.warning_label.setVisible(True)
            self.warning_label.setText(t("gui_tab.warning_developer"))
            self.warning_label.setStyleSheet(
                "QLabel { "
                "background-color: #f8d7da; "
                "color: #721c24; "
                "padding: 10px; "
                "border: 1px solid #f5c6cb; "
                "border-radius: 4px; "
                "}"
            )

    def retranslate(self) -> None:
        """Update all translatable strings."""
        self.config_level_group.setTitle(t("gui_tab.config_level_group"))
        self.config_level_label.setText(t("gui_tab.level"))
        self.config_level_label.setToolTip(t("gui_tab.level_tooltip"))

        self.window_group.setTitle(t("gui_tab.window_behavior_group"))
        self.minimize_label.setText(t("gui_tab.minimize_to_tray"))
        self.minimize_label.setToolTip(t("gui_tab.minimize_tooltip"))
        self.minimize_to_tray_input.setText(t("gui_tab.minimize_checkbox"))

        self.language_group.setTitle(t("gui_tab.language").rstrip(":"))
        self.language_label.setText(t("gui_tab.language"))
        self.language_label.setToolTip(t("gui_tab.language_tooltip"))

        # Update config level items
        for i in range(self.config_level_input.count()):
            data = self.config_level_input.itemData(i)
            if data == ConfigLevel.BASIC:
                self.config_level_input.setItemText(i, t("gui_tab.level_basic"))
            elif data == ConfigLevel.ADVANCED:
                self.config_level_input.setItemText(i, t("gui_tab.level_advanced"))
            elif data == ConfigLevel.DEVELOPER:
                self.config_level_input.setItemText(i, t("gui_tab.level_developer"))

        self._update_warning_visibility()

    def set_values(self, settings: GUISettings) -> None:
        """Set widget values from settings.

        Args:
            settings (GUISettings): GUISettings instance to load values from.
        """
        # Set config level
        index = self.config_level_input.findData(settings.config_level)
        if index >= 0:
            self.config_level_input.setCurrentIndex(index)

        # Set minimize to tray
        self.minimize_to_tray_input.setChecked(settings.minimize_to_tray)

        # Set language
        lang_index = self.language_input.findData(settings.language)
        if lang_index >= 0:
            # Block signals to prevent triggering language change during load
            self.language_input.blockSignals(True)
            self.language_input.setCurrentIndex(lang_index)
            self.language_input.blockSignals(False)

    def get_values(self) -> GUISettings:
        """Get current values from widgets.

        Returns:
            GUISettings: GUISettings instance with current values from widgets
        """
        config_level: ConfigLevel = self.config_level_input.currentData()
        language: str = self.language_input.currentData() or "en"
        return GUISettings(
            config_level=config_level,
            minimize_to_tray=self.minimize_to_tray_input.isChecked(),
            language=language,
        )

    def get_config_level(self) -> ConfigLevel:
        """Get the current config level.

        Returns:
            ConfigLevel: Current configuration level
        """
        level: ConfigLevel = self.config_level_input.currentData()
        return level
