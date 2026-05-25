"""Data model for CLI command information."""

from pydantic import BaseModel, ConfigDict, Field


class CommandInfo(BaseModel):
    """Information about an available CLI command.

    Attributes:
        description: Human-readable description of what the command does
        module: Python module path containing the command implementation
        function: Function name to call within the module (typically 'main')
        aliases: Alternative names that can be used to invoke this command
    """

    description: str = Field(description="Human-readable command description")
    module: str = Field(description="Python module path for the command")
    function: str = Field(description="Function name to call in the module", default="main")
    aliases: list[str] = Field(description="Alternative command names", default_factory=list)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "description": "Scan stockpile screenshots to identify items",
                "module": "foxhole_stockpiles.cli.commands.scan",
                "function": "main",
                "aliases": ["scan", "stockpile-scanner"],
            }
        },
    )
