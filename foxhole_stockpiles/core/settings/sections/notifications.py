"""Notifications settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.notifier_type import NotifierType

# Default message templates for each event type
DEFAULT_TEMPLATES = {
    "stockpile.scanned": (
        "✅ Stockpile **STOCKPILE_NAME** (STOCKPILE_TYPE) scanned in DURATION - ITEM_COUNT items"
    ),
    "stockpile.scan_failed": "❌ Stockpile scan failed: ERROR",
    "stockpile.scan_started": "🔄 Stockpile scan started...",
    "server.started": "🚀 Server started",
    "server.stopped": "🛑 Server stopped",
}


class DiscordNotifierSettings(BaseModel):
    """Settings for Discord notifier."""

    type: NotifierType = Field(description="Notifier type", default=NotifierType.DISCORD)
    name: str = Field(description="Human-readable name for this notifier", default="Discord")
    webhook_url: str = Field(description="Discord webhook URL")
    username: str | None = Field(
        description="Custom username for webhook messages", default="Foxhole Stockpiles"
    )
    events: list[str] = Field(
        description="List of event types to send to Discord",
        default=[
            "stockpile.scanned",
            "stockpile.scan_failed",
        ],
    )
    message_templates: dict[str, str] = Field(
        description="Custom message templates per event type. Available placeholders: "
        "STOCKPILE_NAME, STOCKPILE_TYPE, SHARD, TIME, ITEM_COUNT, "
        "MATCHED_ITEMS, UNMATCHED_ITEMS, AVG_CONFIDENCE, DURATION, "
        "RESOLUTION, ERROR",
        default_factory=dict,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "discord",
                "name": "Main Discord",
                "webhook_url": "https://discord.com/api/webhooks/123456789/abcdef",
                "username": "Stockpile Bot",
                "events": ["stockpile.scanned", "stockpile.scan_failed"],
                "message_templates": {
                    "stockpile.scanned": (
                        "📦 STOCKPILE_NAME @ SHARD [TIME] - ITEM_COUNT items "
                        "(UNMATCHED_ITEMS unknown) - AVG_CONFIDENCE confidence"
                    )
                },
            }
        },
    )


class NotificationsSettings(BaseModel):
    """Settings for notifications system."""

    enabled: bool = Field(description="Enable or disable notifications", default=False)
    notifiers: list[DiscordNotifierSettings] = Field(
        description="List of notifier configurations",
        default_factory=list,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
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
        },
    )
