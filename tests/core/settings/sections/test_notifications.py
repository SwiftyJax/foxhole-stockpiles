"""Tests for core.settings.sections.notifications module.

This module contains comprehensive tests for the notifications settings classes,
which handle configuration for the notification system.
"""

import pytest
from pydantic import ValidationError

from foxhole_stockpiles.core.settings.sections.notifications import (
    DiscordNotifierSettings,
    NotificationsSettings,
)
from foxhole_stockpiles.enums.notifier_type import NotifierType


class TestDiscordNotifierSettings:
    """Test suite for DiscordNotifierSettings.

    This class contains tests for Discord notifier configuration validation.
    """

    def test_discord_notifier_with_webhook_url(self) -> None:
        """Test creating Discord notifier settings with webhook URL."""
        settings = DiscordNotifierSettings(webhook_url="https://discord.com/api/webhooks/123/abc")

        assert settings.type == NotifierType.DISCORD
        assert settings.name == "Discord"
        assert settings.webhook_url == "https://discord.com/api/webhooks/123/abc"
        assert settings.username == "Foxhole Stockpiles"
        assert settings.events == ["stockpile.scanned", "stockpile.scan_failed"]

    def test_discord_notifier_with_custom_values(self) -> None:
        """Test creating Discord notifier with all custom values."""
        settings = DiscordNotifierSettings(
            type=NotifierType.DISCORD,
            name="Custom Discord",
            webhook_url="https://discord.com/api/webhooks/456/def",
            username="Custom Bot",
            events=["server.started", "server.stopped"],
        )

        assert settings.type == NotifierType.DISCORD
        assert settings.name == "Custom Discord"
        assert settings.webhook_url == "https://discord.com/api/webhooks/456/def"
        assert settings.username == "Custom Bot"
        assert settings.events == ["server.started", "server.stopped"]

    def test_discord_notifier_missing_webhook_url(self) -> None:
        """Test that Discord notifier requires webhook_url."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordNotifierSettings()  # type: ignore[call-arg]

        assert "webhook_url" in str(exc_info.value)

    def test_discord_notifier_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden in Discord notifier settings."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordNotifierSettings(
                webhook_url="https://discord.com/api/webhooks/123/abc",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_discord_notifier_type_is_literal(self) -> None:
        """Test that type field is always 'discord'."""
        settings = DiscordNotifierSettings(webhook_url="https://discord.com/api/webhooks/123/abc")

        assert settings.type == NotifierType.DISCORD
        # Type should be the enum value
        assert isinstance(settings.type, NotifierType)

    def test_discord_notifier_empty_events_list(self) -> None:
        """Test Discord notifier with empty events list."""
        settings = DiscordNotifierSettings(
            webhook_url="https://discord.com/api/webhooks/123/abc", events=[]
        )

        assert settings.events == []

    def test_discord_notifier_none_username(self) -> None:
        """Test Discord notifier with None username keeps None."""
        settings = DiscordNotifierSettings(
            webhook_url="https://discord.com/api/webhooks/123/abc", username=None
        )

        # Pydantic allows None since it's specified in the type annotation
        assert settings.username is None


class TestNotificationsSettings:
    """Test suite for NotificationsSettings.

    This class contains tests for notifications system configuration validation.
    """

    def test_notifications_disabled_by_default(self) -> None:
        """Test that notifications are disabled by default."""
        settings = NotificationsSettings()

        assert settings.enabled is False
        assert settings.notifiers == []

    def test_notifications_enabled(self) -> None:
        """Test enabling notifications."""
        settings = NotificationsSettings(enabled=True)

        assert settings.enabled is True

    def test_notifications_with_single_notifier(self) -> None:
        """Test notifications settings with a single Discord notifier."""
        discord_config = DiscordNotifierSettings(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config])

        assert settings.enabled is True
        assert len(settings.notifiers) == 1
        assert settings.notifiers[0].webhook_url == "https://discord.com/api/webhooks/123/abc"

    def test_notifications_with_multiple_notifiers(self) -> None:
        """Test notifications settings with multiple Discord notifiers."""
        discord_config1 = DiscordNotifierSettings(
            name="Discord 1",
            webhook_url="https://discord.com/api/webhooks/111/aaa",
            events=["stockpile.scanned"],
        )
        discord_config2 = DiscordNotifierSettings(
            name="Discord 2",
            webhook_url="https://discord.com/api/webhooks/222/bbb",
            events=["stockpile.scan_failed"],
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config1, discord_config2])

        assert len(settings.notifiers) == 2
        assert settings.notifiers[0].name == "Discord 1"
        assert settings.notifiers[1].name == "Discord 2"

    def test_notifications_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden in notifications settings."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationsSettings(
                enabled=True,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_notifications_empty_notifiers_list(self) -> None:
        """Test notifications with empty notifiers list."""
        settings = NotificationsSettings(enabled=True, notifiers=[])

        assert settings.enabled is True
        assert settings.notifiers == []

    def test_notifications_from_dict(self) -> None:
        """Test creating notifications settings from dictionary."""
        config_dict = {
            "enabled": True,
            "notifiers": [
                {
                    "type": "discord",
                    "name": "Main Discord",
                    "webhook_url": "https://discord.com/api/webhooks/123/abc",
                    "username": "Bot",
                    "events": ["stockpile.scanned"],
                }
            ],
        }

        settings = NotificationsSettings.model_validate(config_dict)

        assert settings.enabled is True
        assert len(settings.notifiers) == 1
        assert settings.notifiers[0].name == "Main Discord"
        assert settings.notifiers[0].webhook_url == "https://discord.com/api/webhooks/123/abc"

    def test_notifications_model_dump(self) -> None:
        """Test serializing notifications settings to dictionary."""
        discord_config = DiscordNotifierSettings(
            name="Test Discord",
            webhook_url="https://discord.com/api/webhooks/123/abc",
            username="Test Bot",
        )
        settings = NotificationsSettings(enabled=True, notifiers=[discord_config])

        config_dict = settings.model_dump()

        assert config_dict["enabled"] is True
        assert len(config_dict["notifiers"]) == 1
        assert config_dict["notifiers"][0]["name"] == "Test Discord"
        assert (
            config_dict["notifiers"][0]["webhook_url"] == "https://discord.com/api/webhooks/123/abc"
        )


class TestNotificationsSettingsExamples:
    """Test suite for NotificationsSettings JSON schema examples.

    This class verifies that the example configurations in the model work correctly.
    """

    def test_discord_notifier_example_is_valid(self) -> None:
        """Test that the Discord notifier example in schema is valid."""
        example = {
            "type": "discord",
            "name": "Main Discord",
            "webhook_url": "https://discord.com/api/webhooks/123456789/abcdef",
            "username": "Stockpile Bot",
            "events": ["stockpile.scanned", "stockpile.scan_failed"],
        }

        settings = DiscordNotifierSettings.model_validate(example)

        assert settings.name == "Main Discord"
        assert settings.webhook_url == "https://discord.com/api/webhooks/123456789/abcdef"

    def test_notifications_settings_example_is_valid(self) -> None:
        """Test that the notifications settings example in schema is valid."""
        example = {
            "enabled": True,
            "notifiers": [
                {
                    "type": "discord",
                    "name": "Main Server",
                    "webhook_url": "https://discord.com/api/webhooks/111/aaa",
                    "username": "Stockpile Bot",
                    "events": ["stockpile.scanned", "stockpile.scan_failed"],
                },
                {
                    "type": "discord",
                    "name": "Admin Channel",
                    "webhook_url": "https://discord.com/api/webhooks/222/bbb",
                    "username": "Admin Bot",
                    "events": ["stockpile.scan_failed", "server.started"],
                },
            ],
        }

        settings = NotificationsSettings.model_validate(example)

        assert settings.enabled is True
        assert len(settings.notifiers) == 2
