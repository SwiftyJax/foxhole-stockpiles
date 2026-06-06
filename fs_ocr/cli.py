"""CLI for fs_ocr package.

Provides the `fs-ocr` command-line interface.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer

from foxhole_stockpiles import __version__
from foxhole_stockpiles.models.stockpile import Stockpile
from fs_ocr.api import (
    SCHEMA_VERSION,
    OCRScanner,
    ScannerConfig,
)

logger = logging.getLogger(__name__)

app = typer.Typer(
    no_args_is_help=True,
    help="Foxhole stockpile OCR tool. Extracts item data from screenshots.",
)


def _setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


@app.command()
def scan(
    image: Annotated[
        str,
        typer.Argument(help="Path to image file, or '-' for stdin"),
    ],
    database: Annotated[
        Path,
        typer.Option("--database", "-d", exists=True, help="Path to HDF5 template database"),
    ],
    tessdata: Annotated[
        str,
        typer.Option("--tessdata", "-t", help="Path to Tesseract data directory"),
    ] = "tessdata",
    early_exit: Annotated[
        float,
        typer.Option("--early-exit", help="Early exit threshold for icon matching (0=disabled)"),
    ] = 0.0,
    compact: Annotated[
        bool,
        typer.Option("--compact", "-c", help="Output compact JSON (no indentation)"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging to stderr"),
    ] = False,
) -> None:
    """Scan an image and output stockpile data as JSON.

    Reads the image, performs OCR to detect items and quantities,
    and outputs the result as JSON to stdout.
    """
    _setup_logging(verbose)

    try:
        # Handle stdin
        if image == "-":
            image_data: bytes | Path = sys.stdin.buffer.read()
        else:
            image_path = Path(image)
            if not image_path.exists():
                typer.echo(f"Error: Image not found: {image}", err=True)
                raise typer.Exit(2)
            image_data = image_path

        # Configure and run scanner
        config = ScannerConfig(
            database_path=database,
            tessdata_path=tessdata,
            early_exit_threshold=early_exit,
        )

        with OCRScanner(config) as scanner:
            result = asyncio.run(scanner.scan(image_data))

        # Output JSON
        indent = None if compact else 2
        output = result.model_dump_json(indent=indent)
        typer.echo(output)

    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2) from None
    except ValueError as e:
        typer.echo(f"Error: Invalid input - {e}", err=True)
        raise typer.Exit(2) from None
    except Exception as e:
        typer.echo(f"Error: Processing failed - {e}", err=True)
        raise typer.Exit(3) from None


@app.command()
def info(
    database: Annotated[
        Path,
        typer.Option("--database", "-d", exists=True, help="Path to HDF5 template database"),
    ],
) -> None:
    """Print scanner version and metadata as JSON."""
    try:
        config = ScannerConfig(database_path=database)
        with OCRScanner(config) as scanner:
            info_obj = scanner.info()
        typer.echo(info_obj.model_dump_json(indent=2))
    except Exception as e:
        logger.debug("info command failed", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def schema() -> None:
    """Print the JSON Schema for the Stockpile output model."""
    schema_dict = Stockpile.model_json_schema()
    schema_dict["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema_dict["title"] = "Stockpile"
    schema_dict["description"] = f"fs-ocr scan output schema (version {SCHEMA_VERSION})"
    typer.echo(json.dumps(schema_dict, indent=2))


@app.command()
def version() -> None:
    """Print version information."""
    typer.echo(f"fs-ocr {__version__} (schema {SCHEMA_VERSION})")


def main() -> None:
    """Entry point for fs-ocr CLI."""
    app()


if __name__ == "__main__":
    main()
