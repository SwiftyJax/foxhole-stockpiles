"""External Tools settings tab."""

from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.external_tools import ExternalToolsSettings


class ExternalToolsTab(QWidget):
    """Tab for External Tools configuration.

    This tab can be configured to show only specific tools based on the context.
    """

    # Download URLs for each tool
    TOOL_URLS = {
        "repak": "https://github.com/trumank/repak/releases",
        "umodel": "https://www.gildor.org/en/projects/umodel",
        "uassetgui": "https://github.com/atenfyr/UAssetGUI/releases",
    }

    # Tool descriptions
    TOOL_DESCRIPTIONS = {
        "repak": (
            "Path to repak executable for extracting PAK files.\n\n"
            "Required for extracting game assets from PAK files.\n"
            "Download from: https://github.com/trumank/repak"
        ),
        "umodel": (
            "Path to umodel executable for converting UAsset files to PNG.\n\n"
            "Required for the 'Build Database' feature.\n"
            "Download from: https://www.gildor.org/en/projects/umodel"
        ),
        "uassetgui": (
            "Path to UAssetGUI executable for converting UAsset files to JSON.\n\n"
            "Required for the 'Build Catalog' feature.\n"
            "Download from: https://github.com/atenfyr/UAssetGUI"
        ),
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        show_repak: bool = True,
        show_umodel: bool = True,
        show_uassetgui: bool = True,
    ) -> None:
        """Initialize the External Tools tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
            show_repak (bool): Whether to show the repak tool. Defaults to True.
            show_umodel (bool): Whether to show the umodel tool. Defaults to True.
            show_uassetgui (bool): Whether to show the uassetgui tool. Defaults to True.
        """
        super().__init__(parent)
        self.show_repak = show_repak
        self.show_umodel = show_umodel
        self.show_uassetgui = show_uassetgui

        # Input widgets (created in init_ui)
        self.repak_input: QLineEdit | None = None
        self.repak_download_btn: QPushButton | None = None
        self.umodel_input: QLineEdit | None = None
        self.umodel_download_btn: QPushButton | None = None
        self.uassetgui_input: QLineEdit | None = None
        self.uassetgui_download_btn: QPushButton | None = None

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Tools Group
        tools_group = QGroupBox("External Tools")
        tools_layout = QFormLayout()
        tools_group.setLayout(tools_layout)

        # Repak tool
        if self.show_repak:
            repak_label = QLabel("Extractor Tool (repak):")
            repak_label.setToolTip(self.TOOL_DESCRIPTIONS["repak"])
            repak_layout = QHBoxLayout()
            self.repak_input = QLineEdit()
            self.repak_input.setPlaceholderText("Path to repak executable")
            self.repak_input.textChanged.connect(self._update_download_buttons)
            repak_layout.addWidget(self.repak_input)
            self.repak_download_btn = QPushButton("Download")
            self.repak_download_btn.setMaximumWidth(80)
            self.repak_download_btn.clicked.connect(lambda: self._open_url(self.TOOL_URLS["repak"]))
            repak_layout.addWidget(self.repak_download_btn)
            repak_browse_btn = QPushButton("Browse...")
            repak_browse_btn.clicked.connect(self._browse_repak)
            repak_layout.addWidget(repak_browse_btn)
            tools_layout.addRow(repak_label, repak_layout)

        # Umodel tool
        if self.show_umodel:
            umodel_label = QLabel("Converter Tool (umodel):")
            umodel_label.setToolTip(self.TOOL_DESCRIPTIONS["umodel"])
            umodel_layout = QHBoxLayout()
            self.umodel_input = QLineEdit()
            self.umodel_input.setPlaceholderText("Path to umodel executable")
            self.umodel_input.textChanged.connect(self._update_download_buttons)
            umodel_layout.addWidget(self.umodel_input)
            self.umodel_download_btn = QPushButton("Download")
            self.umodel_download_btn.setMaximumWidth(80)
            self.umodel_download_btn.clicked.connect(
                lambda: self._open_url(self.TOOL_URLS["umodel"])
            )
            umodel_layout.addWidget(self.umodel_download_btn)
            umodel_browse_btn = QPushButton("Browse...")
            umodel_browse_btn.clicked.connect(self._browse_umodel)
            umodel_layout.addWidget(umodel_browse_btn)
            tools_layout.addRow(umodel_label, umodel_layout)

        # UAssetGUI tool
        if self.show_uassetgui:
            uassetgui_label = QLabel("JSON Converter (UAssetGUI):")
            uassetgui_label.setToolTip(self.TOOL_DESCRIPTIONS["uassetgui"])
            uassetgui_layout = QHBoxLayout()
            self.uassetgui_input = QLineEdit()
            self.uassetgui_input.setPlaceholderText("Path to UAssetGUI executable")
            self.uassetgui_input.textChanged.connect(self._update_download_buttons)
            uassetgui_layout.addWidget(self.uassetgui_input)
            self.uassetgui_download_btn = QPushButton("Download")
            self.uassetgui_download_btn.setMaximumWidth(80)
            self.uassetgui_download_btn.clicked.connect(
                lambda: self._open_url(self.TOOL_URLS["uassetgui"])
            )
            uassetgui_layout.addWidget(self.uassetgui_download_btn)
            uassetgui_browse_btn = QPushButton("Browse...")
            uassetgui_browse_btn.clicked.connect(self._browse_uassetgui)
            uassetgui_layout.addWidget(uassetgui_browse_btn)
            tools_layout.addRow(uassetgui_label, uassetgui_layout)

        layout.addWidget(tools_group)
        layout.addStretch()

        # Initial update of download button visibility
        self._update_download_buttons()

    def _update_download_buttons(self) -> None:
        """Update visibility of download buttons based on whether fields are empty."""
        if self.repak_download_btn and self.repak_input:
            self.repak_download_btn.setVisible(not self.repak_input.text().strip())
        if self.umodel_download_btn and self.umodel_input:
            self.umodel_download_btn.setVisible(not self.umodel_input.text().strip())
        if self.uassetgui_download_btn and self.uassetgui_input:
            self.uassetgui_download_btn.setVisible(not self.uassetgui_input.text().strip())

    def _open_url(self, url: str) -> None:
        """Open URL in default browser.

        Args:
            url (str): URL to open
        """
        QDesktopServices.openUrl(QUrl(url))

    def _browse_repak(self) -> None:
        """Open file dialog to select repak tool."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Extractor Tool (repak)",
            "",
            "All Files (*)",
        )
        if file_path and self.repak_input:
            self.repak_input.setText(file_path)

    def _browse_umodel(self) -> None:
        """Open file dialog to select umodel tool."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Converter Tool (umodel)",
            "",
            "All Files (*)",
        )
        if file_path and self.umodel_input:
            self.umodel_input.setText(file_path)

    def _browse_uassetgui(self) -> None:
        """Open file dialog to select UAssetGUI tool."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select JSON Converter (UAssetGUI)",
            "",
            "All Files (*)",
        )
        if file_path and self.uassetgui_input:
            self.uassetgui_input.setText(file_path)

    def set_values(self, settings: ExternalToolsSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (ExternalToolsSettings): ExternalToolsSettings instance to load
                values from.
        """
        if self.repak_input:
            self.repak_input.setText(str(settings.repak) if settings.repak else "")
        if self.umodel_input:
            self.umodel_input.setText(str(settings.umodel) if settings.umodel else "")
        if self.uassetgui_input:
            self.uassetgui_input.setText(str(settings.uassetgui) if settings.uassetgui else "")

        # Update download button visibility
        self._update_download_buttons()

    def get_values(self) -> ExternalToolsSettings:
        """Get current values from widgets.

        Returns:
            ExternalToolsSettings: ExternalToolsSettings instance with current values
                from widgets. Only includes values for visible tools.
        """
        repak_text = self.repak_input.text().strip() if self.repak_input else ""
        umodel_text = self.umodel_input.text().strip() if self.umodel_input else ""
        uassetgui_text = self.uassetgui_input.text().strip() if self.uassetgui_input else ""

        return ExternalToolsSettings(
            repak=Path(repak_text) if repak_text else None,
            umodel=Path(umodel_text) if umodel_text else None,
            uassetgui=Path(uassetgui_text) if uassetgui_text else None,
        )

    def merge_with_existing(self, existing: ExternalToolsSettings) -> ExternalToolsSettings:
        """Merge current values with existing settings.

        Only updates fields for tools that are shown in this tab.
        This allows partial updates when not all tools are visible.

        Args:
            existing (ExternalToolsSettings): Existing settings to merge with.

        Returns:
            ExternalToolsSettings: Merged settings.
        """
        current = self.get_values()

        # Start with existing values
        merged_data = existing.model_dump()

        # Only update fields for visible tools
        if self.show_repak:
            merged_data["repak"] = current.repak
        if self.show_umodel:
            merged_data["umodel"] = current.umodel
        if self.show_uassetgui:
            merged_data["uassetgui"] = current.uassetgui

        return ExternalToolsSettings(**merged_data)
