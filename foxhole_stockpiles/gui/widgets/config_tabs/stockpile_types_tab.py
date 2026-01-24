"""Stockpile types settings tab."""

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.stockpile_types import StockpileTypesSettings


class StockpileTypesTab(QWidget):
    """Tab for configuring additional stockpile type aliases.

    This tab allows users to add custom aliases for stockpile type names
    to handle OCR errors or other variations in the detected text.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the stockpile types tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self._inputs: dict[str, QLineEdit] = {}
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Description
        description = QLabel(
            "Add custom aliases for stockpile type names to handle OCR errors.\n"
            "Enter comma-separated values (e.g., 'seapon, Seapont, 5eaport').\n"
            "The default translations are already built-in and don't need to be added here."
        )
        description.setWordWrap(True)
        description.setStyleSheet("QLabel { color: gray; margin-bottom: 10px; }")
        layout.addWidget(description)

        # Stockpile Types Group
        types_group = QGroupBox("Additional Aliases")
        types_layout = QFormLayout()
        types_group.setLayout(types_layout)

        # Define fields with their display names and tooltips
        fields = [
            ("encampment", "Encampment", "Aliases for Encampment stockpile type"),
            ("keep", "Keep", "Aliases for Keep stockpile type"),
            ("safe_house", "Safe House", "Aliases for Safe House stockpile type"),
            ("relic_base", "Relic Base", "Aliases for Relic Base stockpile type"),
            ("bunker_base", "Bunker Base", "Aliases for Bunker Base stockpile type"),
            ("border_base", "Border Base", "Aliases for Border Base stockpile type"),
            ("town_base", "Town Base", "Aliases for Town Base stockpile type"),
            ("bms_longhook", "BMS - Longhook", "Aliases for BMS - Longhook stockpile type"),
            ("storage_depot", "Storage Depot", "Aliases for Storage Depot stockpile type"),
            ("seaport", "Seaport", "Aliases for Seaport stockpile type"),
        ]

        for field_name, display_name, tooltip in fields:
            label = QLabel(f"{display_name}:")
            label.setToolTip(tooltip)

            line_edit = QLineEdit()
            line_edit.setPlaceholderText("Enter comma-separated aliases...")
            line_edit.setToolTip(tooltip)

            self._inputs[field_name] = line_edit
            types_layout.addRow(label, line_edit)

        layout.addWidget(types_group)
        layout.addStretch()

    def set_values(self, settings: StockpileTypesSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (StockpileTypesSettings): Settings instance to load values from.
        """
        for field_name, line_edit in self._inputs.items():
            aliases: list[str] = getattr(settings, field_name, [])
            line_edit.setText(", ".join(aliases))

    def get_values(self) -> StockpileTypesSettings:
        """Get current values from widgets.

        Returns:
            StockpileTypesSettings: Settings instance with current values from widgets
        """
        values: dict[str, list[str]] = {}

        for field_name, line_edit in self._inputs.items():
            text = line_edit.text().strip()
            if text:
                # Split by comma and strip whitespace from each alias
                aliases = [alias.strip() for alias in text.split(",") if alias.strip()]
                values[field_name] = aliases
            else:
                values[field_name] = []

        return StockpileTypesSettings(**values)
