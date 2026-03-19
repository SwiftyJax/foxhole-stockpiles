"""Web-specific services for icon retrieval and processing."""

import logging

import cv2

from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.services.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class IconService:
    """Service for retrieving and formatting icons from the template database.

    Retrieves icons from the HDF5 database using the largest available resolution,
    with fallback to vanilla mod if the requested mod doesn't have the icon.
    """

    def __init__(
        self,
        template_manager: TemplateManager,
        default_mod: str = "vanilla",
    ) -> None:
        """Initialize the icon service.

        Args:
            template_manager: The template manager instance for database access.
            default_mod: Default mod to use for icon lookups.
        """
        self._template_manager = template_manager
        self._default_mod = default_mod
        self._icon_cache: dict[tuple[str, bool, str], bytes | None] = {}
        self._largest_resolution: SupportedResolution | None = None
        logger.info("IconService initialized with default_mod=%s", default_mod)

    async def get_icon_png(
        self,
        code: str,
        crated: bool = False,
        mod: str | None = None,
    ) -> bytes | None:
        """Get icon as PNG bytes.

        Args:
            code: Item code to look up.
            crated: Whether to get the crated variant.
            mod: Mod to use. Falls back to vanilla if not found,
                 then to default_mod if specified.

        Returns:
            PNG image bytes or None if not found.
        """
        effective_mod = mod or self._default_mod
        cache_key = (code, crated, effective_mod)

        # Check cache first
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        try:
            # Get the largest available resolution
            if self._largest_resolution is None:
                resolutions = self._template_manager.get_available_resolutions()
                if not resolutions:
                    logger.warning("No resolutions available in database")
                    self._icon_cache[cache_key] = None
                    return None
                self._largest_resolution = max(resolutions, key=lambda r: int(r.value))

            # Load the database for that resolution
            database = await self._template_manager.load_database(self._largest_resolution)

            # Log available mods on first access (info level for diagnostics)
            available_mods = database.get_available_mods()
            if effective_mod not in available_mods and effective_mod != "vanilla":
                logger.warning(
                    "Configured mod '%s' not found in database. Available mods: %s",
                    effective_mod,
                    available_mods,
                )
            else:
                logger.debug(
                    "Available mods in database: %s (looking for mod=%s)",
                    available_mods,
                    effective_mod,
                )

            # Find template matching code, crated, and mod
            template = None

            # Try exact code match with specified mod
            candidates = database.get_candidates(mod=effective_mod, crated=crated)
            logger.debug(
                "get_candidates(mod=%s, crated=%s) returned %d candidates for code=%s",
                effective_mod,
                crated,
                len(candidates),
                code,
            )
            for idx in candidates:
                if database.templates[idx].code == code:
                    template = database.templates[idx]
                    logger.debug("Found template for code=%s in mod=%s", code, effective_mod)
                    break

            # Fallback to vanilla if mod specified and not found
            if template is None and effective_mod != "vanilla":
                logger.info(
                    "Icon '%s' (crated=%s) not found in mod='%s', falling back to vanilla",
                    code,
                    crated,
                    effective_mod,
                )
                for idx in database.get_candidates(mod="vanilla", crated=crated):
                    if database.templates[idx].code == code:
                        template = database.templates[idx]
                        break

            if template is None:
                logger.debug("Icon not found for code=%s, crated=%s, mod=%s", code, crated, mod)
                self._icon_cache[cache_key] = None
                return None

            # Convert BGR numpy array to PNG bytes
            success, png_data = cv2.imencode(".png", template.image)
            if not success:
                logger.error("Failed to encode icon to PNG for code=%s", code)
                self._icon_cache[cache_key] = None
                return None

            png_bytes = png_data.tobytes()
            self._icon_cache[cache_key] = png_bytes
            return png_bytes

        except FileNotFoundError:
            logger.warning("Database file not found")
            self._icon_cache[cache_key] = None
            return None
        except Exception as e:
            logger.error("Error retrieving icon for code=%s: %s", code, e)
            self._icon_cache[cache_key] = None
            return None
