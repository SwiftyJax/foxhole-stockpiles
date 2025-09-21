"""FastAPI server for Foxhole stockpile scanning."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import copy
from typing import Any

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import AppSettings, get_settings
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.handlers.output_handler import OutputHandler
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Health status")
    version: str = Field(description="Application version")


# Global settings
app_settings: AppSettings = get_settings()


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
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Root endpoint returning basic API information.

    Returns:
        HealthResponse: Basic API status and version information
    """
    return HealthResponse(status="running", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse: Application health status and version

    Raises:
        HTTPException: If application settings not initialized (503 status)
    """
    return HealthResponse(status="healthy", version="0.1.0")


@app.post("/ocr/scan_image")
async def scan_stockpile(
    image: UploadFile,
    request: Request,
    faction: str | None = Query(default=None, description="Faction filter (colonials or wardens)"),
) -> Any:
    """Scan a stockpile screenshot and return detected items.

    Args:
        image (UploadFile): Screenshot image file (PNG, JPG, JPEG supported)
        request (Request): FastAPI request object
        faction (str | None): Optional faction filter to limit detection to specific faction items

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

        rgb_image = np.asarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), dtype=np.uint8)

        config = copy(app_settings.scanner)
        config.faction_filter = ItemFaction.from_string(faction)
        if config.faction_filter == ItemFaction.NEUTRAL:
            config.faction_filter = None

        request_coordinator = OCRCoordinator(config)
        stockpile = await request_coordinator.analyze_stockpile(rgb_image)

        # Read the token from the specified header if configured
        if app_settings.output_format.webhook_client_auth_header:
            token = request.headers.get(app_settings.output_format.webhook_client_auth_header)
        else:
            token = None

        output_handler = OutputHandler(settings=app_settings)
        return await output_handler.handle_output(
            stockpile=stockpile, output_format=app_settings.output_format.output_format, token=token
        )

    except ValueError as e:
        logger = logging.getLogger(__name__)
        logger.error("Validation error during processing: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Processing error: {str(e)}"
        ) from None
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error during processing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}"
        ) from None


def main() -> None:
    """Run the FastAPI server.

    Starts the FastAPI application using uvicorn on port 8000.
    """
    uvicorn.run(app, port=8000, log_level="info")


if __name__ == "__main__":
    main()
