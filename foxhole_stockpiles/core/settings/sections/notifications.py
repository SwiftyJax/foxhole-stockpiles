"""Notifications settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.notifier_type import NotifierType


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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "discord",
                "name": "Main Discord",
                "webhook_url": "https://discord.com/api/webhooks/123456789/abcdef",
                "username": "Stockpile Bot",
                "events": ["stockpile.scanned", "stockpile.scan_failed"],
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
