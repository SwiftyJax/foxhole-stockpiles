"""Pydantic models for database and template manager statistics."""

from pydantic import BaseModel, Field


class DatabaseStatistics(BaseModel):
    """Statistics for a template database."""

    resolution: int = Field(description="Resolution height in pixels")
    total_templates: int = Field(description="Total number of templates in the database")
    faction_counts: dict[str, int] = Field(description="Count of templates by faction")
    mod_counts: dict[str, int] = Field(description="Count of templates by mod")
    crated_templates: int = Field(description="Number of crated template variants")
    normal_templates: int = Field(description="Number of normal (non-crated) template variants")


class TemplateManagerStatistics(BaseModel):
    """Statistics for the template manager and active database."""

    loaded_resolutions: int = Field(
        description="Number of resolution databases currently loaded in memory"
    )
    current_resolution: str | None = Field(
        description="Currently active resolution as string, or None if no database is active"
    )
    active_templates: int = Field(
        description="Number of templates in the currently active database"
    )

    # Include database statistics if an active database exists
    resolution: int | None = Field(
        default=None, description="Resolution height in pixels of active database"
    )
    total_templates: int | None = Field(
        default=None, description="Total number of templates in active database"
    )
    faction_counts: dict[str, int] | None = Field(
        default=None, description="Count of templates by faction in active database"
    )
    mod_counts: dict[str, int] | None = Field(
        default=None, description="Count of templates by mod in active database"
    )
    crated_templates: int | None = Field(
        default=None, description="Number of crated template variants in active database"
    )
    normal_templates: int | None = Field(
        default=None, description="Number of normal template variants in active database"
    )

    @classmethod
    def from_manager_and_database(
        cls,
        loaded_resolutions: int,
        current_resolution: str | None,
        active_templates: int,
        database_stats: DatabaseStatistics | None = None,
    ) -> "TemplateManagerStatistics":
        """Create TemplateManagerStatistics from manager data and optional database stats.

        Args:
            loaded_resolutions (int): Number of loaded resolution databases
            current_resolution (str | None): Current active resolution string
            active_templates (int): Number of templates in active database
            database_stats (DatabaseStatistics | None): Optional database statistics

        Returns:
            TemplateManagerStatistics: Complete statistics object
        """
        if database_stats:
            return cls(
                loaded_resolutions=loaded_resolutions,
                current_resolution=current_resolution,
                active_templates=active_templates,
                resolution=database_stats.resolution,
                total_templates=database_stats.total_templates,
                faction_counts=database_stats.faction_counts,
                mod_counts=database_stats.mod_counts,
                crated_templates=database_stats.crated_templates,
                normal_templates=database_stats.normal_templates,
            )

        return cls(
            loaded_resolutions=loaded_resolutions,
            current_resolution=current_resolution,
            active_templates=active_templates,
        )
