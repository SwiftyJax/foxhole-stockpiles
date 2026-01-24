"""Discord webhook notifier."""

import logging
from typing import Any

from discord_webhook import AsyncDiscordWebhook, DiscordEmbed  # type: ignore[import-untyped]

from foxhole_stockpiles.enums.event_type import EventType
from foxhole_stockpiles.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class DiscordNotifier(BaseNotifier):
    """Send notifications to Discord via webhooks."""

    def __init__(
        self,
        webhook_url: str,
        username: str | None = None,
        message_templates: dict[str, str] | None = None,
    ) -> None:
        """Initialize Discord notifier.

        Args:
            webhook_url (str): Discord webhook URL
            username (str | None): Optional custom username for webhook messages
            message_templates (dict[str, str] | None): Custom message templates per event type
        """
        super().__init__("Discord")
        self.webhook_url = webhook_url
        self.username = f"FS ({username or 'Foxhole Stockpiles'})"
        self.message_templates = message_templates or {}

    async def send(self, event_type: str, data: dict[str, Any]) -> None:
        """Send notification to Discord.

        Args:
            event_type (str): The type of event
            data (dict[str, Any]): Event data

        Raises:
            Exception: If the Discord API request fails
        """
        if not self.enabled:
            logger.debug(f"Notifier '{self.name}' is disabled, skipping notification")
            return

        message = self.format_message(event_type, data)
        embed = self._create_embed(event_type, data)

        try:
            webhook = AsyncDiscordWebhook(
                url=self.webhook_url,
                content=message,
                username=self.username,
                rate_limit_retry=True,
            )

            if embed:
                webhook.add_embed(embed)

            response = await webhook.execute()
            if response.status_code not in (200, 204):
                logger.error(
                    f"Discord API returned status {response.status_code}: {response.content}"
                )
            else:
                logger.debug(f"Discord notification sent for event '{event_type}'")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            raise

    def format_message(self, event_type: str, data: dict[str, Any]) -> str:
        """Format event into Discord message.

        Args:
            event_type (str): The type of event
            data (dict[str, Any]): Event data

        Returns:
            str: Formatted message
        """
        # Import default templates
        from foxhole_stockpiles.core.settings.sections.notifications import DEFAULT_TEMPLATES

        # Use custom template if provided, otherwise use default
        template = self.message_templates.get(event_type) or DEFAULT_TEMPLATES.get(
            event_type, f"Event: {event_type}"
        )

        # Prepare replacement values with safe defaults and formatting
        replacements = {
            "STOCKPILE_NAME": data.get("stockpile_name", "Unknown"),
            "STOCKPILE_TYPE": data.get("stockpile_type", "Unknown"),
            "SHARD": data.get("shard", "Unknown"),
            "TIME": data.get("time", "Unknown"),
            "ITEM_COUNT": str(data.get("item_count", 0)),
            "MATCHED_ITEMS": str(data.get("matched_items", 0)),
            "UNMATCHED_ITEMS": str(data.get("unmatched_items", 0)),
            "AVG_CONFIDENCE": f"{data.get('avg_confidence', 0.0):.1%}",
            "DURATION": f"{data.get('duration', 0.0):.2f}s",
            "RESOLUTION": data.get("resolution", "Unknown"),
            "ERROR": data.get("error", "Unknown error"),
        }

        # Perform string replacement (sorted by length descending to avoid partial replacements)
        message = template
        for placeholder in sorted(replacements.keys(), key=len, reverse=True):
            message = message.replace(placeholder, replacements[placeholder])

        return message

    def _create_embed(self, event_type: str, data: dict[str, Any]) -> DiscordEmbed | None:
        """Create Discord embed for rich formatting.

        Args:
            event_type (str): The type of event
            data (dict[str, Any]): Event data

        Returns:
            DiscordEmbed | None: Discord embed object or None if no embed needed
        """
        # Only create embeds for successful scans with details
        if event_type != EventType.STOCKPILE_SCANNED:
            return None

        embed = DiscordEmbed(title="Scan Complete", color="2ECC71")

        # Add relevant fields
        if "stockpile_name" in data:
            embed.add_embed_field(name="Stockpile", value=data["stockpile_name"], inline=True)

        if "duration" in data:
            embed.add_embed_field(name="Duration", value=f"{data['duration']:.2f}s", inline=True)

        if "item_count" in data:
            embed.add_embed_field(name="Items Found", value=str(data["item_count"]), inline=True)

        if "resolution" in data:
            embed.add_embed_field(name="Resolution", value=data["resolution"], inline=True)

        if "timestamp" in data:
            embed.set_timestamp(timestamp=data["timestamp"])

        return embed
