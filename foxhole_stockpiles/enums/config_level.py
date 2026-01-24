"""Enum for GUI configuration levels."""

from enum import StrEnum
from typing import Self


class ConfigLevel(StrEnum):
    """Configuration level for GUI visibility.

    Levels are ordered from least to most permissive:
    BASIC < ADVANCED < DEVELOPER
    """

    BASIC = "basic"
    ADVANCED = "advanced"
    DEVELOPER = "developer"

    def is_at_least(self, level: Self) -> bool:
        """Check if this level is at least the given level.

        Args:
            level: The minimum level to check against.

        Returns:
            True if this level is equal to or higher than the given level.
        """
        order = list(ConfigLevel)
        return order.index(self) >= order.index(level)
