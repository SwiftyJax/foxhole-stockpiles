"""Template database for resolution-specific template storage and filtering."""

import logging

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate

logger = logging.getLogger(__name__)


class TemplateDatabase:
    """Resolution-specific template database with basic faction and mod filtering."""

    def __init__(self, resolution: SupportedResolution) -> None:
        """Initialize template database.

        Args:
            resolution (SupportedResolution): Target resolution for this database
        """
        self.resolution = resolution
        self.templates: list[IconTemplate] = []

        # Basic lookup tables for faction, mod, and category filtering
        self.faction_lookup: dict[str, list[int]] = {}
        self.mod_lookup: dict[str, list[int]] = {}
        self.category_lookup: dict[str, list[int]] = {}

    def add_template(self, template: IconTemplate) -> None:
        """Add template and update lookup tables.

        Args:
            template (IconTemplate): Template to add to database
        """
        idx = len(self.templates)
        self.templates.append(template)

        # Update faction lookup
        if template.faction.value not in self.faction_lookup:
            self.faction_lookup[template.faction.value] = []
        self.faction_lookup[template.faction.value].append(idx)

        # Update mod lookup
        if template.mod not in self.mod_lookup:
            self.mod_lookup[template.mod] = []
        self.mod_lookup[template.mod].append(idx)

        # Update category lookup
        if template.category.value not in self.category_lookup:
            self.category_lookup[template.category.value] = []
        self.category_lookup[template.category.value].append(idx)

    def get_candidates(
        self,
        faction: ItemFaction | None = None,
        mod: str | None = None,
        category: ItemCategory | None = None,
        crated: bool | None = None,
        code: str | None = None,
        excluded_codes: list[str] | None = None,
    ) -> list[int]:
        """Get candidate template indices using faction, mod, category, and crated filters.

        Args:
            faction (ItemFaction | None): Optional faction filter
            mod (str | None): Optional mod filter
            category (ItemCategory | None): Optional category filter
            crated (bool | None): Optional crated filter (True for crated only,
                False for normal only, None for both)
            code (str | None): Optional item code filter
            excluded_codes (list[str] | None): Optional list of item codes to exclude from results

        Returns:
            list[int]: Candidate template indices for matching
        """
        candidates = set(range(len(self.templates)))

        if code:
            # Filter by item code if specified
            candidates = {i for i in candidates if code in self.templates[i].code}

        # Apply category filter if specified
        if category and category != ItemCategory.Invalid:
            category_candidates = self.category_lookup.get(category.value, [])
            candidates = candidates & set(category_candidates)

        # Apply mod filter if specified
        if mod:
            mod_candidates = self.mod_lookup.get(mod, [])
            candidates = candidates & set(mod_candidates)

        # Apply faction filter if specified
        if faction and faction != ItemFaction.NEUTRAL:
            faction_candidates = self.faction_lookup.get(faction.value, [])
            # Also include neutral items
            neutral_candidates = self.faction_lookup.get(ItemFaction.NEUTRAL.value, [])
            valid_faction_candidates = set(faction_candidates + neutral_candidates)
            candidates = candidates & valid_faction_candidates

        # Apply crated filter if specified
        if crated is not None:
            crated_candidates = []
            for idx in candidates:
                template = self.templates[idx]
                if template.crated == crated:
                    crated_candidates.append(idx)
            candidates = set(crated_candidates)

        # Apply excluded_codes filter if specified
        if excluded_codes:
            excluded_candidates = []
            for idx in candidates:
                template = self.templates[idx]
                if template.code not in excluded_codes:
                    excluded_candidates.append(idx)
            candidates = set(excluded_candidates)

        logger.debug(
            (
                "Candidate filtering: faction=%s, mod=%s, category=%s, crated=%s, "
                "candidates=%d, code=%s, excluded_codes=%s"
            ),
            faction.value if faction else "any",
            mod or "any",
            category.value if category else "any",
            crated if crated is not None else "any",
            len(candidates),
            code or "any",
            excluded_codes or "none",
        )

        return list(candidates)

    def __len__(self) -> int:
        """Return number of templates in database."""
        return len(self.templates)

    def __repr__(self) -> str:
        """String representation of the database."""
        return (
            f"TemplateDatabase(resolution={self.resolution.value}, "
            f"templates={len(self.templates)}, "
            f"factions={len(self.faction_lookup)}, "
            f"mods={len(self.mod_lookup)})"
        )
