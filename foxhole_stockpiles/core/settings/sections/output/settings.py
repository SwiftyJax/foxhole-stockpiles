"""Output settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.core.settings.sections.output.handler_config import (
    OutputHandlerConfig,
)


class OutputSettings(BaseModel):
    """Settings for output handlers."""

    handlers: list[OutputHandlerConfig] = Field(
        description="List of output handler configurations",
        default_factory=list,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "handlers": [
                    {
                        "name": "API Response",
                        "format": {"type": "json"},
                        "handler": {"type": "return"},
                    },
                    {
                        "name": "Webhook",
                        "format": {"type": "json"},
                        "handler": {
                            "type": "webhook",
                            "url": "https://api.example.com/stockpiles",
                            "auth_type": "bearer",
                            "token": "your-token",
                        },
                    },
                    {
                        "name": "CSV Backup",
                        "format": {
                            "type": "csv",
                            "separator": ",",
                            "fields": ["code", "quantity", "crated"],
                        },
                        "handler": {
                            "type": "file",
                            "path": "stockpiles/{timestamp}.csv",
                        },
                    },
                ]
            }
        },
    )
