"""Tests for notifiers.discord module.

This module contains comprehensive tests for the DiscordNotifier class,
which handles sending notifications to Discord via webhooks.
"""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from discord_webhook import DiscordEmbed  # type: ignore[import-untyped]

from foxhole_stockpiles.enums.event_type import EventType
from foxhole_stockpiles.notifiers.discord import DiscordNotifier


class TestDiscordNotifierInitialization:
    """Test suite for DiscordNotifier initialization.

    This class contains tests for proper initialization of the DiscordNotifier
    including webhook URL, username, and initial state validation.
    """

    def test_init_with_webhook_url_only(self) -> None:
        """Test initializing DiscordNotifier with only webhook URL."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")

        assert notifier.webhook_url == "https://discord.com/api/webhooks/123/abc"
        assert notifier.username == "Foxhole Stockpiles"
        assert notifier.name == "Discord"
        assert notifier.enabled is True

    def test_init_with_custom_username(self) -> None:
        """Test initializing DiscordNotifier with custom username."""
        notifier = DiscordNotifier(
            webhook_url="https://discord.com/api/webhooks/123/abc", username="Custom Bot"
        )

        assert notifier.username == "Custom Bot"


class TestSend:
    """Test suite for DiscordNotifier.send method.

    This class contains tests for sending notifications to Discord.
    """

    @pytest.mark.asyncio
    async def test_send_success(self) -> None:
        """Test successfully sending a notification."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        test_data = {
            "stockpile_name": "Test Stockpile",
            "stockpile_type": "Public",
            "duration": 1.5,
            "item_count": 10,
        }

        with patch("foxhole_stockpiles.notifiers.discord.AsyncDiscordWebhook") as mock_webhook:
            mock_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_instance.execute.return_value = mock_response
            mock_webhook.return_value = mock_instance

            await notifier.send(EventType.STOCKPILE_SCANNED, test_data)

            mock_webhook.assert_called_once()
            mock_instance.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_when_disabled(self) -> None:
        """Test that send does nothing when notifier is disabled."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        notifier.enabled = False
        test_data = {"key": "value"}

        with patch("foxhole_stockpiles.notifiers.discord.AsyncDiscordWebhook") as mock_webhook:
            await notifier.send(EventType.STOCKPILE_SCANNED, test_data)

            mock_webhook.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_with_embed(self) -> None:
        """Test sending a notification with an embed."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        test_data = {
            "stockpile_name": "Test Stockpile",
            "stockpile_type": "Public",
            "duration": 1.5,
            "item_count": 10,
            "resolution": "1920x1080",
            "timestamp": "2025-01-01T12:00:00",
        }

        with patch("foxhole_stockpiles.notifiers.discord.AsyncDiscordWebhook") as mock_webhook:
            mock_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_instance.execute.return_value = mock_response
            mock_webhook.return_value = mock_instance

            await notifier.send(EventType.STOCKPILE_SCANNED, test_data)

            # Verify embed was added
            mock_instance.add_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_handles_api_error(self) -> None:
        """Test that send raises exception when Discord API returns error."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        test_data = {"key": "value"}

        with patch("foxhole_stockpiles.notifiers.discord.AsyncDiscordWebhook") as mock_webhook:
            mock_instance = AsyncMock()
            mock_instance.execute.side_effect = Exception("API Error")
            mock_webhook.return_value = mock_instance

            with pytest.raises(Exception, match="API Error"):
                await notifier.send(EventType.STOCKPILE_SCANNED, test_data)

    @pytest.mark.asyncio
    async def test_send_handles_non_200_status(self) -> None:
        """Test that send logs error when Discord API returns non-200 status."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        test_data = {"key": "value"}

        with patch("foxhole_stockpiles.notifiers.discord.AsyncDiscordWebhook") as mock_webhook:
            mock_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.content = b"Bad Request"
            mock_instance.execute.return_value = mock_response
            mock_webhook.return_value = mock_instance

            with patch("foxhole_stockpiles.notifiers.discord.logger") as mock_logger:
                await notifier.send(EventType.STOCKPILE_SCANNED, test_data)
                mock_logger.error.assert_called()


class TestFormatMessage:
    """Test suite for DiscordNotifier.format_message method.

    This class contains tests for formatting event data into Discord messages.
    """

    def test_format_stockpile_scanned_message(self) -> None:
        """Test formatting a STOCKPILE_SCANNED event message."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data = {
            "stockpile_name": "Armory Alpha",
            "stockpile_type": "Public",
            "duration": 2.34,
            "item_count": 15,
        }

        message = notifier.format_message(EventType.STOCKPILE_SCANNED, data)

        assert "Armory Alpha" in message
        assert "Public" in message
        assert "2.34s" in message
        assert "15 items" in message
        assert "✅" in message

    def test_format_stockpile_scan_failed_message(self) -> None:
        """Test formatting a STOCKPILE_SCAN_FAILED event message."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data = {"error": "Image too small"}

        message = notifier.format_message(EventType.STOCKPILE_SCAN_FAILED, data)

        assert "Image too small" in message
        assert "❌" in message

    def test_format_stockpile_scan_started_message(self) -> None:
        """Test formatting a STOCKPILE_SCAN_STARTED event message."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data: dict[str, Any] = {}

        message = notifier.format_message(EventType.STOCKPILE_SCAN_STARTED, data)

        assert "started" in message.lower()
        assert "🔄" in message

    def test_format_server_started_message(self) -> None:
        """Test formatting a SERVER_STARTED event message."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data = {"host": "localhost", "port": 8000}

        message = notifier.format_message(EventType.SERVER_STARTED, data)

        assert "localhost:8000" in message
        assert "🚀" in message

    def test_format_server_stopped_message(self) -> None:
        """Test formatting a SERVER_STOPPED event message."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data: dict[str, Any] = {}

        message = notifier.format_message(EventType.SERVER_STOPPED, data)

        assert "stopped" in message.lower()
        assert "🛑" in message

    def test_format_unknown_event_type(self) -> None:
        """Test formatting an unknown event type falls back to default."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data = {"test": "value"}

        message = notifier.format_message("unknown.event", data)

        # Should fall back to base class format_message
        assert isinstance(message, str)


class TestCreateEmbed:
    """Test suite for DiscordNotifier._create_embed method.

    This class contains tests for creating Discord embeds.
    """

    def test_create_embed_for_stockpile_scanned(self) -> None:
        """Test creating an embed for STOCKPILE_SCANNED event."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data = {
            "stockpile_name": "Armory Alpha",
            "duration": 2.34,
            "item_count": 15,
            "resolution": "1920x1080",
            "timestamp": "2025-01-01T12:00:00",
        }

        embed = notifier._create_embed(EventType.STOCKPILE_SCANNED, data)

        assert embed is not None
        assert isinstance(embed, DiscordEmbed)

    def test_create_embed_returns_none_for_other_events(self) -> None:
        """Test that _create_embed returns None for non-STOCKPILE_SCANNED events."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data = {"error": "Test error"}

        embed = notifier._create_embed(EventType.STOCKPILE_SCAN_FAILED, data)

        assert embed is None

    def test_create_embed_with_minimal_data(self) -> None:
        """Test creating an embed with minimal data (just stockpile_name)."""
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc")
        data = {"stockpile_name": "Armory Alpha"}

        embed = notifier._create_embed(EventType.STOCKPILE_SCANNED, data)

        assert embed is not None
        assert isinstance(embed, DiscordEmbed)
