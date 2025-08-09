"""Template database for resolution-specific template storage and filtering."""

import logging

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.database_statistics import DatabaseStatistics
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
    ) -> list[int]:
        """Get candidate template indices using faction, mod, category, and crated filters.

        Args:
            faction (ItemFaction | None): Optional faction filter
            mod (str | None): Optional mod filter
            category (ItemCategory | None): Optional category filter
            crated (bool | None): Optional crated filter (True for crated only,
                False for normal only, None for both)
            code (str | None): Optional item code filter

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
        if faction:
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

        logger.debug(
            (
                "Candidate filtering: faction=%s, mod=%s, category=%s, crated=%s, "
                "candidates=%d, code=%s"
            ),
            faction.value if faction else "any",
            mod or "any",
            category.value if category else "any",
            crated if crated is not None else "any",
            len(candidates),
            code or "any",
        )

        return list(candidates)

    def get_statistics(self) -> DatabaseStatistics:
        """Get database statistics.

        Returns:
            DatabaseStatistics: Database statistics as Pydantic model
        """
        faction_counts: dict[str, int] = {}
        mod_counts: dict[str, int] = {}
        crated_count = 0

        for template in self.templates:
            # Count by faction
            faction_counts[template.faction.value] = (
                faction_counts.get(template.faction.value, 0) + 1
            )
            # Count by mod
            mod_counts[template.mod] = mod_counts.get(template.mod, 0) + 1
            # Count crated items
            if template.crated:
                crated_count += 1

        # Sort faction counts with neutral first, then Colonials, then Wardens
        faction_order = ["neutral", "Colonials", "Wardens"]
        sorted_faction_counts = {}
        for faction in faction_order:
            if faction in faction_counts:
                sorted_faction_counts[faction] = faction_counts[faction]

        # Sort mod counts with vanilla first, then alphabetical
        sorted_mod_counts = {}
        if "vanilla" in mod_counts:
            sorted_mod_counts["vanilla"] = mod_counts["vanilla"]

        # Add remaining mods in alphabetical order
        for mod in sorted(mod_counts.keys()):
            if mod != "vanilla":
                sorted_mod_counts[mod] = mod_counts[mod]

        return DatabaseStatistics(
            resolution=int(self.resolution.value),
            total_templates=len(self.templates),
            faction_counts=sorted_faction_counts,
            mod_counts=sorted_mod_counts,
            crated_templates=crated_count,
            normal_templates=len(self.templates) - crated_count,
        )

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
