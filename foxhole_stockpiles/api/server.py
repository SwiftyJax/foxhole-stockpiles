"""FastAPI server for Foxhole stockpile scanning."""

import gc
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import cv2
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from foxhole_stockpiles import __version__
from foxhole_stockpiles.api.auth import create_auth_dependency
from foxhole_stockpiles.api.dependencies import (
    get_notification_service,
    get_ocr_coordinator,
    get_output_coordinator,
)
from foxhole_stockpiles.api.memory_middleware import MemoryMonitorMiddleware
from foxhole_stockpiles.api.web.routes import router as web_router
from foxhole_stockpiles.core.events import get_event_bus
from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import AppSettings, get_settings
from foxhole_stockpiles.core.settings.sections.output import WebhookHandlerSettings
from foxhole_stockpiles.core.utils import get_tesseract_version
from foxhole_stockpiles.core.version import get_version_info
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.event_type import EventType
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
memory_monitor = MemoryMonitor(history_size=100, snapshot_interval=50)


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
    logger.info("Starting Foxhole Stockpile Scanner API v%s", get_version_info())
    logger.info("Database path: %s", app_settings.scanner.database_path)

    # Check if Tesseract is accessible (using our wrapper to avoid console flash on Windows)
    version = get_tesseract_version()
    if version:
        logger.info("Tesseract OCR version: %s", version)
    else:
        error_msg = (
            "Tesseract OCR not found. Required for processing stockpile scans.\n\n"
            "Download and install Tesseract:\n"
            "• Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "• Linux: sudo apt install tesseract-ocr\n"
            "• macOS: brew install tesseract\n\n"
            "After installation, ensure tesseract is in your system PATH."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Initialize notification service if enabled
    if app_settings.notifications.enabled:
        notification_service = get_notification_service()
        logger.info(
            "Notification service initialized with %d notifier(s)",
            len(notification_service.notifiers),
        )

    # Emit server started event
    event_bus = get_event_bus()
    event_bus.emit(EventType.SERVER_STARTED, {})

    yield

    # Send server stopped notification before shutdown (must await to ensure it's sent)
    if app_settings.notifications.enabled:
        try:
            notification_service = get_notification_service()
            await notification_service.send_notification(EventType.SERVER_STOPPED, {})
        except Exception as e:
            logger.error("Failed to send server stopped notification: %s", e)

    # Emit server stopped event for other subscribers
    event_bus.emit(EventType.SERVER_STOPPED, {})

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

# Add memory middleware if either monitoring or auto-trimming is enabled
if app_settings.api_server.enable_memory_monitoring or app_settings.api_server.auto_trim_memory:
    app.add_middleware(
        MemoryMonitorMiddleware,
        monitor=memory_monitor,
        auto_trim_after_scan=app_settings.api_server.auto_trim_memory,
        enable_monitoring=app_settings.api_server.enable_memory_monitoring,
    )

# Create authentication dependency
auth_dependency = create_auth_dependency(app_settings.api_auth)

# Include web router (provides "/" and "/web/*" endpoints) with auth
app.include_router(web_router, dependencies=[Depends(auth_dependency)])


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
    coordinator: Annotated[OCRCoordinator, Depends(get_ocr_coordinator)],
    output_coordinator: Annotated[OutputCoordinator, Depends(get_output_coordinator)],
    faction: Annotated[
        ItemFaction | None, Query(description="Faction filter (Colonials or Wardens)")
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
        coordinator (OCRCoordinator): OCR coordinator singleton (injected)
        output_coordinator (OutputCoordinator): Output coordinator singleton (injected)
        faction (ItemFaction | None): Optional faction filter to limit detection to specific
            faction items
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

        # Treat NEUTRAL as None (no faction filter)
        faction_filter = faction if faction != ItemFaction.NEUTRAL else None

        stockpile = await coordinator.analyze_stockpile(
            image=image_bgr, language=language, faction=faction_filter
        )

        # Read the token from the specified header if any webhook handler uses forward auth
        token = None
        for handler_config in app_settings.output.handlers:
            handler = handler_config.handler
            if isinstance(handler, WebhookHandlerSettings):
                if handler.auth_type == AuthType.FORWARD and handler.client_auth_header:
                    token = request.headers.get(handler.client_auth_header)
                    break  # Use the first forward auth header found

        return await output_coordinator.handle_output(
            stockpile=stockpile,
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


@app.get("/memory/stats", dependencies=[Depends(auth_dependency)])
async def memory_stats() -> dict[str, Any]:
    """Get memory usage statistics.

    Returns:
        dict[str, Any]: Memory statistics including current usage, trends, and history
    """
    return memory_monitor.get_statistics()


@app.post("/memory/gc", dependencies=[Depends(auth_dependency)])
async def force_garbage_collection() -> dict[str, Any]:
    """Force garbage collection and return statistics.

    Returns:
        dict[str, Any]: Garbage collection results including freed memory
    """
    return memory_monitor.force_garbage_collection()


@app.get("/memory/current", dependencies=[Depends(auth_dependency)])
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


@app.get("/memory/gc-stats", dependencies=[Depends(auth_dependency)])
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
