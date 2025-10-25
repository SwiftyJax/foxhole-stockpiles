"""FastAPI server for Foxhole stockpile scanning."""

import gc
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import copy
from typing import Annotated, Any

import cv2
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from foxhole_stockpiles import __version__
from foxhole_stockpiles.api.auth import create_auth_dependency
from foxhole_stockpiles.api.memory_middleware import MemoryMonitorMiddleware
from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import AppSettings, get_settings
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_language import SupportedLanguage
from foxhole_stockpiles.services.memory_monitor import MemoryMonitor
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator
from foxhole_stockpiles.services.output_coordinator import OutputCoordinator


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Health status")
    version: str = Field(description="Application version")


# Global settings
app_settings: AppSettings = get_settings()

# Global memory monitor
memory_monitor = MemoryMonitor(history_size=1000, snapshot_interval=100)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan event handler for initialization and cleanup.

    Args:
        app (FastAPI): FastAPI application instance

    Yields:
        None: Control back to FastAPI after initialization
    """
    setup_logging(app_settings.logging)
    logger = logging.getLogger(__name__)
    logger.info("Starting Foxhole Stockpile Scanner API")
    logger.info("Database path: %s", app_settings.scanner.database_path)

    yield

    # Shutdown
    logger.info("Shutting down Foxhole Stockpile Scanner API")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Foxhole Stockpile Scanner API",
    description="API for analyzing Foxhole stockpile screenshots and extracting item data",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.api_server.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add memory monitoring middleware
app.add_middleware(MemoryMonitorMiddleware, monitor=memory_monitor)

# Create authentication dependency
auth_dependency = create_auth_dependency(app_settings.api_auth)


@app.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Root endpoint returning basic API information.

    Returns:
        HealthResponse: Basic API status and version information
    """
    return HealthResponse(status="running", version=__version__)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse: Application health status and version

    Raises:
        HTTPException: If application settings not initialized (503 status)
    """
    return HealthResponse(status="healthy", version=__version__)


@app.post("/ocr/scan_image", dependencies=[Depends(auth_dependency)])
async def scan_stockpile(
    image: UploadFile,
    request: Request,
    faction: Annotated[
        ItemFaction | None, Query(description="Faction filter (Colonials or Wardens)")
    ] = None,
    mod_name: Annotated[
        str | None, Query(max_length=50, description="Mod name filter (max 50 chars)")
    ] = None,
    language: Annotated[
        SupportedLanguage | None,
        Query(description="Language for text detection (en, pt, fr, de, ru, zh)"),
    ] = None,
) -> Any:
    """Scan a stockpile screenshot and return detected items.

    Args:
        image (UploadFile): Screenshot image file (PNG, JPG, JPEG supported)
        request (Request): FastAPI request object
        faction (ItemFaction | None): Optional faction filter to limit detection to specific
            faction items
        mod_name (str | None): Optional mod name filter (max 50 chars)
        language (SupportedLanguage | None): Optional language for text detection. If None,
            uses all supported languages.

    Returns:
        Any: Output from configured output handler
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    try:
        content = await image.read()

        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format or corrupted image data",
            )

        image_bgr = np.asarray(img, dtype=np.uint8)

        config = copy(app_settings.scanner)
        # Set faction filter, treating NEUTRAL as None (no filter)
        config.faction_filter = faction if faction != ItemFaction.NEUTRAL else None
        config.mod_name = mod_name
        config.language = language

        request_coordinator = OCRCoordinator(config)
        stockpile = await request_coordinator.analyze_stockpile(image_bgr)

        # Read the token from the specified header if configured
        if app_settings.output.webhook.client_auth_header:
            token = request.headers.get(app_settings.output.webhook.client_auth_header)
        else:
            token = None

        output_coordinator = OutputCoordinator(settings=app_settings)
        return await output_coordinator.handle_output(
            stockpile=stockpile,
            destination=app_settings.output.destination,
            token=token,
        )

    except ValueError as e:
        logger = logging.getLogger(__name__)
        error_msg = str(e)

        # Check if it's a mod validation error
        if "not supported" in error_msg and "Available mods:" in error_msg:
            logger.error("Mod validation error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error_msg
            ) from None

        # Other validation errors
        logger.error("Validation error during processing: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Processing error: {error_msg}"
        ) from None
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error during processing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}"
        ) from None


@app.get("/memory/stats")
async def memory_stats() -> dict[str, Any]:
    """Get memory usage statistics.

    Returns:
        dict[str, Any]: Memory statistics including current usage, trends, and history
    """
    return memory_monitor.get_statistics()


@app.post("/memory/gc")
async def force_garbage_collection() -> dict[str, Any]:
    """Force garbage collection and return statistics.

    Returns:
        dict[str, Any]: Garbage collection results including freed memory
    """
    return memory_monitor.force_garbage_collection()


@app.get("/memory/current")
async def current_memory() -> dict[str, Any]:
    """Get current memory snapshot.

    Returns:
        dict[str, Any]: Current memory usage snapshot
    """
    snapshot = memory_monitor.get_current_memory()
    return {
        "timestamp": snapshot.timestamp.isoformat(),
        "rss_mb": round(snapshot.rss_mb, 2),
        "vms_mb": round(snapshot.vms_mb, 2),
        "percent": round(snapshot.percent, 2),
        "available_mb": round(snapshot.available_mb, 2),
    }


@app.get("/memory/gc-stats")
async def garbage_collection_stats() -> dict[str, Any]:
    """Get garbage collector statistics.

    Returns:
        dict[str, Any]: Garbage collector statistics and object counts
    """
    gc_stats = gc.get_stats()
    gc_count = gc.get_count()

    # Get count of tracked objects by type
    objects = gc.get_objects()
    type_counts: dict[str, int] = {}

    for obj in objects[:1000]:  # Limit to first 1000 for performance
        obj_type = type(obj).__name__
        type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

    # Sort by count
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "gc_enabled": gc.isenabled(),
        "generation_counts": {
            "generation_0": gc_count[0],
            "generation_1": gc_count[1],
            "generation_2": gc_count[2],
        },
        "total_tracked_objects": len(objects),
        "top_object_types": [{"type": t, "count": c} for t, c in sorted_types],
        "gc_stats": gc_stats,
    }
