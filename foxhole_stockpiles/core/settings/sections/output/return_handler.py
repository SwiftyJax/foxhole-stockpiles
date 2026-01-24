"""Return handler settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.output_handler_type import OutputHandlerType


class ReturnHandlerSettings(BaseModel):
    """Settings for return output handler (API response)."""

    type: OutputHandlerType = Field(default=OutputHandlerType.RETURN, description="Handler type")

    model_config = ConfigDict(extra="forbid")
