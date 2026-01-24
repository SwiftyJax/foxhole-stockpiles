"""Tests for NotificationsTab."""

from typing import Any
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QDialog, QMessageBox

from foxhole_stockpiles.core.settings.sections.notifications import (
    DiscordNotifierSettings,
    NotificationsSettings,
)
from foxhole_stockpiles.enums.notifier_type import NotifierType
from foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab import (
    NotificationsTab,
    NotifierDialog,
)


@pytest.fixture
def notifications_tab(qtbot: Any) -> NotificationsTab:
    """Create a NotificationsTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        NotificationsTab: Tab instance
    """
    tab = NotificationsTab()
    qtbot.addWidget(tab)
    return tab


@pytest.fixture
def sample_notifier() -> DiscordNotifierSettings:
    """Create a sample Discord notifier.

    Returns:
        DiscordNotifierSettings: Sample notifier
    """
    return DiscordNotifierSettings(
        type=NotifierType.DISCORD,
        name="Test Discord",
        webhook_url="https://discord.com/api/webhooks/123/abc",
        username="Test Bot",
        events=["stockpile.scanned", "stockpile.scan_failed"],
        message_templates={"stockpile.scanned": "Custom message: STOCKPILE_NAME"},
    )


class TestNotificationsTabInitialization:
    """Tests for NotificationsTab initialization."""

    def test_initialization(self, notifications_tab: NotificationsTab) -> None:
        """Test NotificationsTab initialization.

        Args:
            notifications_tab: NotificationsTab instance
        """
        assert notifications_tab.enabled_checkbox is not None
        assert notifications_tab.notifiers_list is not None
        assert notifications_tab.add_button is not None
        assert notifications_tab.edit_button is not None
        assert notifications_tab.remove_button is not None

    def test_initial_state(self, notifications_tab: NotificationsTab) -> None:
        """Test initial state is disabled with no notifiers.

        Args:
            notifications_tab: NotificationsTab instance
        """
        assert not notifications_tab.enabled_checkbox.isChecked()
        assert notifications_tab.notifiers_list.count() == 0
        assert len(notifications_tab._notifiers) == 0

    def test_edit_remove_buttons_disabled_initially(
        self, notifications_tab: NotificationsTab
    ) -> None:
        """Test edit and remove buttons are disabled when no selection.

        Args:
            notifications_tab: NotificationsTab instance
        """
        assert not notifications_tab.edit_button.isEnabled()
        assert not notifications_tab.remove_button.isEnabled()


class TestNotificationsTabSetValues:
    """Tests for NotificationsTab set_values method."""

    def test_set_values_enabled(
        self, notifications_tab: NotificationsTab, sample_notifier: DiscordNotifierSettings
    ) -> None:
        """Test setting values with enabled notifications.

        Args:
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        settings = NotificationsSettings(enabled=True, notifiers=[sample_notifier])

        notifications_tab.set_values(settings)

        assert notifications_tab.enabled_checkbox.isChecked()
        assert notifications_tab.notifiers_list.count() == 1
        assert len(notifications_tab._notifiers) == 1

    def test_set_values_disabled(
        self, notifications_tab: NotificationsTab, sample_notifier: DiscordNotifierSettings
    ) -> None:
        """Test setting values with disabled notifications.

        Args:
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        settings = NotificationsSettings(enabled=False, notifiers=[sample_notifier])

        notifications_tab.set_values(settings)

        assert not notifications_tab.enabled_checkbox.isChecked()
        assert notifications_tab.notifiers_list.count() == 1

    def test_set_values_empty(self, notifications_tab: NotificationsTab) -> None:
        """Test setting empty values.

        Args:
            notifications_tab: NotificationsTab instance
        """
        settings = NotificationsSettings()

        notifications_tab.set_values(settings)

        assert not notifications_tab.enabled_checkbox.isChecked()
        assert notifications_tab.notifiers_list.count() == 0

    def test_set_values_multiple_notifiers(self, notifications_tab: NotificationsTab) -> None:
        """Test setting values with multiple notifiers.

        Args:
            notifications_tab: NotificationsTab instance
        """
        notifiers = [
            DiscordNotifierSettings(
                name="Notifier 1",
                webhook_url="https://discord.com/api/webhooks/111/aaa",
                events=["stockpile.scanned"],
            ),
            DiscordNotifierSettings(
                name="Notifier 2",
                webhook_url="https://discord.com/api/webhooks/222/bbb",
                events=["stockpile.scan_failed"],
            ),
        ]
        settings = NotificationsSettings(enabled=True, notifiers=notifiers)

        notifications_tab.set_values(settings)

        assert notifications_tab.notifiers_list.count() == 2
        assert len(notifications_tab._notifiers) == 2

    def test_set_values_notifier_with_many_events(
        self, notifications_tab: NotificationsTab
    ) -> None:
        """Test list display for notifier with more than 2 events.

        Args:
            notifications_tab: NotificationsTab instance
        """
        notifier = DiscordNotifierSettings(
            name="Multi-Event",
            webhook_url="https://discord.com/api/webhooks/333/ccc",
            events=[
                "stockpile.scanned",
                "stockpile.scan_failed",
                "server.started",
                "server.stopped",
            ],
        )
        settings = NotificationsSettings(enabled=True, notifiers=[notifier])

        notifications_tab.set_values(settings)

        assert notifications_tab.notifiers_list.count() == 1
        item = notifications_tab.notifiers_list.item(0)
        assert item is not None
        assert "(+2 more)" in item.text()


class TestNotificationsTabGetValues:
    """Tests for NotificationsTab get_values method."""

    def test_get_values_default(self, notifications_tab: NotificationsTab) -> None:
        """Test getting default values.

        Args:
            notifications_tab: NotificationsTab instance
        """
        settings = notifications_tab.get_values()

        assert not settings.enabled
        assert len(settings.notifiers) == 0

    def test_get_values_with_notifiers(
        self, notifications_tab: NotificationsTab, sample_notifier: DiscordNotifierSettings
    ) -> None:
        """Test getting values with notifiers.

        Args:
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        notifications_tab.enabled_checkbox.setChecked(True)
        notifications_tab._notifiers = [sample_notifier]
        notifications_tab._update_list()

        settings = notifications_tab.get_values()

        assert settings.enabled
        assert len(settings.notifiers) == 1
        assert settings.notifiers[0].name == "Test Discord"
        assert settings.notifiers[0].webhook_url == "https://discord.com/api/webhooks/123/abc"

    def test_roundtrip(
        self, notifications_tab: NotificationsTab, sample_notifier: DiscordNotifierSettings
    ) -> None:
        """Test that set_values and get_values preserve data.

        Args:
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        original = NotificationsSettings(enabled=True, notifiers=[sample_notifier])

        notifications_tab.set_values(original)
        result = notifications_tab.get_values()

        assert result.enabled == original.enabled
        assert len(result.notifiers) == len(original.notifiers)
        assert result.notifiers[0].name == original.notifiers[0].name
        assert result.notifiers[0].webhook_url == original.notifiers[0].webhook_url
        assert result.notifiers[0].events == original.notifiers[0].events


class TestNotificationsTabButtons:
    """Tests for add/edit/remove button handlers."""

    def test_on_add_clicked_accepted(
        self,
        qtbot: Any,
        notifications_tab: NotificationsTab,
        sample_notifier: DiscordNotifierSettings,
    ) -> None:
        """Test adding a notifier when dialog is accepted.

        Args:
            qtbot: PyQt test fixture
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        with patch(
            "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.NotifierDialog"
        ) as mock_dialog_class:
            mock_dialog = mock_dialog_class.return_value
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_notifier.return_value = sample_notifier

            notifications_tab._on_add_clicked()

            assert len(notifications_tab._notifiers) == 1
            assert notifications_tab._notifiers[0] == sample_notifier
            assert notifications_tab.notifiers_list.count() == 1
            assert notifications_tab.notifiers_list.currentRow() == 0

    def test_on_add_clicked_cancelled(self, notifications_tab: NotificationsTab) -> None:
        """Test adding a notifier when dialog is cancelled.

        Args:
            notifications_tab: NotificationsTab instance
        """
        with patch(
            "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.NotifierDialog"
        ) as mock_dialog_class:
            mock_dialog = mock_dialog_class.return_value
            mock_dialog.exec.return_value = QDialog.DialogCode.Rejected

            notifications_tab._on_add_clicked()

            assert len(notifications_tab._notifiers) == 0
            assert notifications_tab.notifiers_list.count() == 0

    def test_on_edit_clicked_no_selection(self, notifications_tab: NotificationsTab) -> None:
        """Test edit click with no selection does nothing.

        Args:
            notifications_tab: NotificationsTab instance
        """
        # No items, no selection
        notifications_tab._on_edit_clicked()
        # Should not raise, just return early
        assert len(notifications_tab._notifiers) == 0

    def test_on_edit_clicked_accepted(
        self,
        notifications_tab: NotificationsTab,
        sample_notifier: DiscordNotifierSettings,
    ) -> None:
        """Test editing a notifier when dialog is accepted.

        Args:
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        # Add initial notifier
        notifications_tab._notifiers = [sample_notifier]
        notifications_tab._update_list()
        notifications_tab.notifiers_list.setCurrentRow(0)

        updated_notifier = DiscordNotifierSettings(
            name="Updated Name",
            webhook_url="https://discord.com/api/webhooks/999/updated",
            events=["server.started"],
        )

        with patch(
            "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.NotifierDialog"
        ) as mock_dialog_class:
            mock_dialog = mock_dialog_class.return_value
            mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog.get_notifier.return_value = updated_notifier

            notifications_tab._on_edit_clicked()

            assert len(notifications_tab._notifiers) == 1
            assert notifications_tab._notifiers[0].name == "Updated Name"
            assert notifications_tab.notifiers_list.currentRow() == 0

    def test_on_remove_clicked_no_selection(self, notifications_tab: NotificationsTab) -> None:
        """Test remove click with no selection does nothing.

        Args:
            notifications_tab: NotificationsTab instance
        """
        # No items, no selection
        notifications_tab._on_remove_clicked()
        # Should not raise, just return early
        assert len(notifications_tab._notifiers) == 0

    def test_on_remove_clicked_confirmed(
        self,
        notifications_tab: NotificationsTab,
        sample_notifier: DiscordNotifierSettings,
    ) -> None:
        """Test removing a notifier when user confirms.

        Args:
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        notifications_tab._notifiers = [sample_notifier]
        notifications_tab._update_list()
        notifications_tab.notifiers_list.setCurrentRow(0)

        with patch(
            "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            notifications_tab._on_remove_clicked()

            assert len(notifications_tab._notifiers) == 0
            assert notifications_tab.notifiers_list.count() == 0

    def test_on_remove_clicked_cancelled(
        self,
        notifications_tab: NotificationsTab,
        sample_notifier: DiscordNotifierSettings,
    ) -> None:
        """Test removing a notifier when user cancels.

        Args:
            notifications_tab: NotificationsTab instance
            sample_notifier: Sample notifier
        """
        notifications_tab._notifiers = [sample_notifier]
        notifications_tab._update_list()
        notifications_tab.notifiers_list.setCurrentRow(0)

        with patch(
            "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ):
            notifications_tab._on_remove_clicked()

            # Notifier should still be there
            assert len(notifications_tab._notifiers) == 1
            assert notifications_tab.notifiers_list.count() == 1


class TestNotificationsTabEnabledState:
    """Tests for notifications enabled state handling."""

    def test_notifiers_group_disabled_when_unchecked(
        self, notifications_tab: NotificationsTab
    ) -> None:
        """Test that notifiers group is disabled when notifications are disabled.

        Args:
            notifications_tab: NotificationsTab instance
        """
        notifications_tab.enabled_checkbox.setChecked(False)
        notifications_tab._on_enabled_changed()

        assert not notifications_tab.notifiers_group.isEnabled()

    def test_notifiers_group_enabled_when_checked(
        self, notifications_tab: NotificationsTab
    ) -> None:
        """Test that notifiers group is enabled when notifications are enabled.

        Args:
            notifications_tab: NotificationsTab instance
        """
        notifications_tab.enabled_checkbox.setChecked(True)
        notifications_tab._on_enabled_changed()

        assert notifications_tab.notifiers_group.isEnabled()


class TestNotifierDialog:
    """Tests for NotifierDialog."""

    def test_dialog_initialization_new(self, qtbot: Any) -> None:
        """Test dialog initialization for new notifier.

        Args:
            qtbot: PyQt test fixture
        """
        dialog = NotifierDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Add Notifier"
        assert dialog.name_input.text() == ""
        assert dialog.webhook_input.text() == ""

    def test_dialog_initialization_edit(
        self, qtbot: Any, sample_notifier: DiscordNotifierSettings
    ) -> None:
        """Test dialog initialization for editing existing notifier.

        Args:
            qtbot: PyQt test fixture
            sample_notifier: Sample notifier
        """
        dialog = NotifierDialog(notifier=sample_notifier)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Edit Notifier"
        assert dialog.name_input.text() == "Test Discord"
        assert dialog.webhook_input.text() == "https://discord.com/api/webhooks/123/abc"
        assert dialog.username_input.text() == "Test Bot"
        assert dialog.event_checkboxes["stockpile.scanned"].isChecked()
        assert dialog.event_checkboxes["stockpile.scan_failed"].isChecked()
        assert not dialog.event_checkboxes["server.started"].isChecked()

    def test_dialog_get_notifier(self, qtbot: Any) -> None:
        """Test getting notifier from dialog.

        Args:
            qtbot: PyQt test fixture
        """
        dialog = NotifierDialog()
        qtbot.addWidget(dialog)

        dialog.name_input.setText("My Notifier")
        dialog.webhook_input.setText("https://discord.com/api/webhooks/999/xyz")
        dialog.username_input.setText("My Bot")
        dialog.event_checkboxes["stockpile.scanned"].setChecked(True)
        dialog.event_checkboxes["server.started"].setChecked(True)
        dialog.template_inputs["stockpile.scanned"].setText("Custom: STOCKPILE_NAME")

        notifier = dialog.get_notifier()

        assert notifier.name == "My Notifier"
        assert notifier.webhook_url == "https://discord.com/api/webhooks/999/xyz"
        assert notifier.username == "My Bot"
        assert "stockpile.scanned" in notifier.events
        assert "server.started" in notifier.events
        assert notifier.message_templates["stockpile.scanned"] == "Custom: STOCKPILE_NAME"

    def test_dialog_default_name(self, qtbot: Any) -> None:
        """Test default name when name input is empty.

        Args:
            qtbot: PyQt test fixture
        """
        dialog = NotifierDialog()
        qtbot.addWidget(dialog)

        dialog.webhook_input.setText("https://discord.com/api/webhooks/999/xyz")
        dialog.event_checkboxes["stockpile.scanned"].setChecked(True)

        notifier = dialog.get_notifier()

        assert notifier.name == "Discord"

    def test_dialog_validation_empty_webhook(self, qtbot: Any) -> None:
        """Test validation fails for empty webhook.

        Args:
            qtbot: PyQt test fixture
        """
        dialog = NotifierDialog()
        qtbot.addWidget(dialog)

        dialog.event_checkboxes["stockpile.scanned"].setChecked(True)

        with (
            patch(
                "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.QMessageBox.warning"
            ),
            patch.object(dialog, "accept") as mock_accept,
        ):
            dialog.validate_and_accept()
            mock_accept.assert_not_called()

    def test_dialog_validation_invalid_webhook(self, qtbot: Any) -> None:
        """Test validation fails for invalid webhook URL.

        Args:
            qtbot: PyQt test fixture
        """
        dialog = NotifierDialog()
        qtbot.addWidget(dialog)

        dialog.webhook_input.setText("https://example.com/webhook")
        dialog.event_checkboxes["stockpile.scanned"].setChecked(True)

        with (
            patch(
                "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.QMessageBox.warning"
            ),
            patch.object(dialog, "accept") as mock_accept,
        ):
            dialog.validate_and_accept()
            mock_accept.assert_not_called()

    def test_dialog_validation_no_events(self, qtbot: Any) -> None:
        """Test validation fails when no events selected.

        Args:
            qtbot: PyQt test fixture
        """
        dialog = NotifierDialog()
        qtbot.addWidget(dialog)

        dialog.webhook_input.setText("https://discord.com/api/webhooks/123/abc")
        # No events checked

        with (
            patch(
                "foxhole_stockpiles.gui.widgets.config_tabs.notifications_tab.QMessageBox.warning"
            ),
            patch.object(dialog, "accept") as mock_accept,
        ):
            dialog.validate_and_accept()
            mock_accept.assert_not_called()

    def test_dialog_validation_success(self, qtbot: Any) -> None:
        """Test validation succeeds with valid input.

        Args:
            qtbot: PyQt test fixture
        """
        dialog = NotifierDialog()
        qtbot.addWidget(dialog)

        dialog.webhook_input.setText("https://discord.com/api/webhooks/123/abc")
        dialog.event_checkboxes["stockpile.scanned"].setChecked(True)

        with patch.object(dialog, "accept") as mock_accept:
            dialog.validate_and_accept()
            mock_accept.assert_called_once()
