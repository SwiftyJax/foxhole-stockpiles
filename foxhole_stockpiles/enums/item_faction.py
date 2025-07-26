"""Faction for items."""

from enum import StrEnum


class ItemFaction(StrEnum):
    """Faction variants for items."""

    NEUTRAL = "neutral"
    COLONIALS = "Colonials"
    WARDENS = "Wardens"

    @classmethod
    def from_string(cls, value: str | None = None) -> "ItemFaction":
        """Convert a string to a Faction, never returns None.

        Args:
            value (str | None): The string to convert. Can be a faction name, abbreviation, or None.

        Returns:
            Faction: The corresponding Faction, defaults to NEUTRAL for invalid/empty input.
        """
        if not value:
            return cls.NEUTRAL

        # Normalize input for comparison
        normalized = value.strip().lower()

        if normalized in ["efactionid::colonials", "colonials", "c"]:
            return cls.COLONIALS

        if normalized in ["efactionid::wardens", "wardens", "w"]:
            return cls.WARDENS

        # Default to NEUTRAL for any invalid input
        return cls.NEUTRAL

    @staticmethod
    def get_cli_help_text() -> str:
        """Get formatted help text for CLI faction parameter.

        Returns:
            str: Formatted help text describing valid faction inputs and filtering behavior
        """
        return (
            "Faction filter - shows items available to specified faction. "
            "Valid inputs: 'c', 'colonials' for Colonials; 'w', 'wardens' for Wardens. "
            "When specified, includes faction-specific items PLUS items available to both factions."
        )

    @staticmethod
    def validate_cli_faction(faction_input: str | None) -> "ItemFaction":
        """Validate CLI faction input and return faction or exit on error.

        Args:
            faction_input (str | None): User input from command line

        Returns:
            Faction: Validated faction (COLONIALS or WARDENS)

        Raises:
            SystemExit: If faction is invalid (including NEUTRAL)
        """
        faction = ItemFaction.from_string(value=faction_input)

        if faction == ItemFaction.NEUTRAL:
            # Invalid input resulted in NEUTRAL
            print(f"❌ Error: Invalid faction '{faction_input}'.")
            print(f"Valid options: {ItemFaction.get_cli_help_text()}")
            print("Only 'colonials' or 'wardens' are allowed for faction filtering.")
            exit(1)

        return faction
