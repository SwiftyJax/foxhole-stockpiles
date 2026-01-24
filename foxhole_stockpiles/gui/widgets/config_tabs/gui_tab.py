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
        config_level_group = QGroupBox("Configuration Level")
        config_level_layout = QFormLayout()
        config_level_group.setLayout(config_level_layout)

        # Config Level Dropdown
        config_level_label = QLabel("Level:")
        config_level_label.setToolTip(
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
        config_level_layout.addRow(config_level_label, self.config_level_input)

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

        layout.addWidget(config_level_group)

        # Window Behavior Group
        window_group = QGroupBox("Window Behavior")
        window_layout = QFormLayout()
        window_group.setLayout(window_layout)

        # Minimize to Tray
        minimize_label = QLabel("Minimize to Tray:")
        minimize_label.setToolTip(
            "When enabled, closing the window minimizes to system tray\n"
            "instead of quitting the application.\n\n"
            "The application will continue running in the background.\n"
            "Right-click the tray icon to access options or quit."
        )
        self.minimize_to_tray_input = QCheckBox("Minimize to tray on close")
        window_layout.addRow(minimize_label, self.minimize_to_tray_input)

        layout.addWidget(window_group)
        layout.addStretch()

        # Initialize warning visibility
        self._update_warning_visibility()

    def _update_warning_visibility(self) -> None:
        """Update warning label visibility and text based on selected level."""
        level = self.config_level_input.currentData()

        if level == "basic":
            self.warning_label.setVisible(False)
        elif level == "advanced":
            self.warning_label.setVisible(True)
            self.warning_label.setText(
                "Advanced mode enables additional options that affect scan accuracy.\n"
                "Only modify these settings if you understand their impact."
            )
        else:  # developer
            self.warning_label.setVisible(True)
            self.warning_label.setText(
                "Developer mode enables critical settings including OCR and Template tabs.\n"
                "Incorrect configuration can completely break scanning functionality.\n"
                "Only use this if you are a developer or advanced user who understands the risks."
            )
            self.warning_label.setStyleSheet(
                "QLabel { "
                "background-color: #f8d7da; "
                "color: #721c24; "
                "padding: 10px; "
                "border: 1px solid #f5c6cb; "
                "border-radius: 4px; "
                "}"
            )

        # Reset style for advanced (in case switching from developer)
        if level == "advanced":
            self.warning_label.setStyleSheet(
                "QLabel { "
                "background-color: #fff3cd; "
                "color: #856404; "
                "padding: 10px; "
                "border: 1px solid #ffc107; "
                "border-radius: 4px; "
                "}"
            )

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

    def get_values(self) -> GUISettings:
        """Get current values from widgets.

        Returns:
            GUISettings: GUISettings instance with current values from widgets
        """
        config_level: ConfigLevel = self.config_level_input.currentData()
        return GUISettings(
            config_level=config_level,
            minimize_to_tray=self.minimize_to_tray_input.isChecked(),
        )

    def get_config_level(self) -> ConfigLevel:
        """Get the current config level.

        Returns:
            ConfigLevel: Current configuration level
        """
        level: ConfigLevel = self.config_level_input.currentData()
        return level
