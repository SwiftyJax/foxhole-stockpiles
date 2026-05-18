"""Stockpile types settings tab."""

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.constants import STOCKPILE_TYPE_TEXTS
from foxhole_stockpiles.core.settings.sections.stockpile_types import StockpileTypesSettings
from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t

# Build fields from StockpileTypesSettings, using STOCKPILE_TYPE_TEXTS for display names
# Field names are snake_case matching StockpileType enum names (e.g., "bunker_base_1")
STOCKPILE_TYPE_FIELDS: list[tuple[str, str]] = []
for field_name in StockpileTypesSettings.model_fields:
    # Convert snake_case field name to enum name (uppercase)
    enum_name = field_name.upper()
    try:
        stockpile_type = StockpileType[enum_name]
    except KeyError:
        continue
    if stockpile_type in STOCKPILE_TYPE_TEXTS:
        display_name = STOCKPILE_TYPE_TEXTS[stockpile_type][0]
        # Add tier suffix for tiered types (those ending with _1, _2, _3)
        if field_name[-2:-1] == "_" and field_name[-1].isdigit():
            display_name += f" T{field_name[-1]}"
        STOCKPILE_TYPE_FIELDS.append((field_name, display_name))


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
        self._labels: dict[str, QLabel] = {}
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("QLabel { color: gray; margin-bottom: 10px; }")
        layout.addWidget(self.description_label)

        # Stockpile Types Group
        self.types_group = QGroupBox()
        types_layout = QFormLayout()
        self.types_group.setLayout(types_layout)

        for field_name, display_name in STOCKPILE_TYPE_FIELDS:
            label = QLabel(f"{display_name}:")

            line_edit = QLineEdit()

            self._labels[field_name] = label
            self._inputs[field_name] = line_edit
            types_layout.addRow(label, line_edit)

        layout.addWidget(self.types_group)
        layout.addStretch()

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
        self.description_label.setText(t("stockpile_types_tab.description"))
        self.types_group.setTitle(t("stockpile_types_tab.aliases_group"))

        placeholder = t("stockpile_types_tab.alias_placeholder")
        for _field_name, line_edit in self._inputs.items():
            line_edit.setPlaceholderText(placeholder)

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
