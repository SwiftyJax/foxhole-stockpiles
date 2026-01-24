"""Console handler settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.output_handler_type import OutputHandlerType


class ConsoleHandlerSettings(BaseModel):
    """Settings for console output handler."""

    type: OutputHandlerType = Field(default=OutputHandlerType.CONSOLE, description="Handler type")

    model_config = ConfigDict(extra="forbid")
