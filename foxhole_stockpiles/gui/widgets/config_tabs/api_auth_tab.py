"""API Authentication settings tab."""

from PyQt6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.api import APIAuthSettings
from foxhole_stockpiles.enums.auth_type import AuthType


class APIAuthTab(QWidget):
    """Tab for API Authentication configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the API Authentication tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Auth Type Selection with Radio Buttons
        auth_type_group = QGroupBox("Authentication Type")
        auth_type_layout = QHBoxLayout()
        auth_type_group.setLayout(auth_type_layout)

        self.auth_type_button_group = QButtonGroup(self)

        self.no_auth_radio = QRadioButton("No Authentication")
        self.no_auth_radio.setChecked(True)
        self.no_auth_radio.setToolTip(
            "API server will accept requests from anyone without authentication."
        )
        self.auth_type_button_group.addButton(self.no_auth_radio, 0)
        auth_type_layout.addWidget(self.no_auth_radio)

        self.basic_auth_radio = QRadioButton("Basic Auth")
        self.basic_auth_radio.setToolTip(
            "Require username and password for API access.\n"
            "Credentials are sent with each request in the Authorization header."
        )
        self.auth_type_button_group.addButton(self.basic_auth_radio, 1)
        auth_type_layout.addWidget(self.basic_auth_radio)

        self.bearer_auth_radio = QRadioButton("Bearer Token")
        self.bearer_auth_radio.setToolTip(
            "Require a bearer token for API access.\n"
            "Token is sent in the Authorization header with each request."
        )
        self.auth_type_button_group.addButton(self.bearer_auth_radio, 2)
        auth_type_layout.addWidget(self.bearer_auth_radio)

        self.auth_type_button_group.buttonClicked.connect(self._update_auth_visibility)

        layout.addWidget(auth_type_group)

        # Basic Auth Group
        self.basic_auth_group = QGroupBox("Basic Authentication")
        basic_layout = QFormLayout()
        self.basic_auth_group.setLayout(basic_layout)

        username_label = QLabel("Username:")
        username_label.setToolTip("Username required for API authentication.")
        self.basic_username_input = QLineEdit()
        self.basic_username_input.setPlaceholderText("Username")
        basic_layout.addRow(username_label, self.basic_username_input)

        password_label = QLabel("Password:")
        password_label.setToolTip("Password required for API authentication.")
        self.basic_password_input = QLineEdit()
        self.basic_password_input.setPlaceholderText("Password")
        self.basic_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        basic_layout.addRow(password_label, self.basic_password_input)

        layout.addWidget(self.basic_auth_group)

        # Bearer Token Group
        self.bearer_auth_group = QGroupBox("Bearer Token Authentication")
        bearer_layout = QFormLayout()
        self.bearer_auth_group.setLayout(bearer_layout)

        token_label = QLabel("Token:")
        token_label.setToolTip(
            "Secret token required for API authentication.\n"
            "This token should be kept secure and sent in the Authorization header."
        )
        self.bearer_token_input = QLineEdit()
        self.bearer_token_input.setPlaceholderText("Enter bearer token")
        self.bearer_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        bearer_layout.addRow(token_label, self.bearer_token_input)

        layout.addWidget(self.bearer_auth_group)

        layout.addStretch()

        # Initially show/hide based on default selection
        self._update_auth_visibility()

    def _update_auth_visibility(self) -> None:
        """Update visibility of auth groups based on selected radio button."""
        # Show/hide groups based on selection
        self.basic_auth_group.setVisible(self.basic_auth_radio.isChecked())
        self.bearer_auth_group.setVisible(self.bearer_auth_radio.isChecked())

    def set_values(self, settings: APIAuthSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (APIAuthSettings): APIAuthSettings instance to load values from.
        """
        # Set auth type radio button
        auth_type = settings.auth_type or "null"
        if auth_type == "basic":
            self.basic_auth_radio.setChecked(True)
        elif auth_type == "bearer":
            self.bearer_auth_radio.setChecked(True)
        else:
            self.no_auth_radio.setChecked(True)

        # Parse and set credentials based on type
        if settings.auth_token:
            if auth_type == "basic":
                # Basic auth token format: "username:password"
                if ":" in settings.auth_token:
                    username, password = settings.auth_token.split(":", 1)
                    self.basic_username_input.setText(username)
                    self.basic_password_input.setText(password)
                else:
                    # Fallback if no colon
                    self.basic_username_input.setText(settings.auth_token)
            elif auth_type == "bearer":
                # Bearer token is just the token value
                self.bearer_token_input.setText(settings.auth_token)

        # Update visibility based on selection
        self._update_auth_visibility()

    def get_values(self) -> APIAuthSettings:
        """Get current values from widgets.

        Returns:
            APIAuthSettings: APIAuthSettings instance with current values from widgets
        """
        # Determine auth type from radio buttons
        if self.basic_auth_radio.isChecked():
            auth_type = "basic"
        elif self.bearer_auth_radio.isChecked():
            auth_type = "bearer"
        else:
            auth_type = "null"

        # Build auth token based on type
        auth_token = None
        if auth_type == "basic":
            username = self.basic_username_input.text().strip()
            password = self.basic_password_input.text().strip()
            if username or password:
                # Store as "username:password"
                auth_token = f"{username}:{password}"
        elif auth_type == "bearer":
            token = self.bearer_token_input.text().strip()
            if token:
                auth_token = token

        return APIAuthSettings(
            auth_type=None if auth_type == "null" else AuthType(auth_type),
            auth_token=auth_token,
        )
