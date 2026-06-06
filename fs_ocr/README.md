# fs-ocr

OCR module for extracting item data from Foxhole stockpile screenshots.

## Overview

`fs-ocr` analyzes game screenshots to detect:
- Stockpile type (Seaport, Storage Depot, etc.)
- Stockpile name
- All items with quantities
- Crated status for applicable items

## CLI Usage

```bash
# Scan an image
fs-ocr scan screenshot.png --database data/templates.h5

# Scan from stdin
cat screenshot.png | fs-ocr scan - --database data/templates.h5

# Compact JSON output
fs-ocr scan screenshot.png --database data/templates.h5 --compact

# View scanner info
fs-ocr info --database data/templates.h5

# View output schema
fs-ocr schema

# Version information
fs-ocr version
```

## Python API

```python
import asyncio
from pathlib import Path
from foxhole_stockpiles.fs_ocr import OCRScanner, ScannerConfig

# Configure scanner
config = ScannerConfig(
    database_path=Path("data/templates.h5"),
    icon_match_threshold=0.85,
)

# Scan an image
async def main():
    with OCRScanner(config) as scanner:
        result = await scanner.scan(Path("screenshot.png"))

        print(f"Stockpile: {result.name} ({result.type})")
        for item in result.items:
            crated = " (crated)" if item.crated else ""
            print(f"  {item.code}: {item.quantity}{crated}")

asyncio.run(main())
```

## Output Format

The scanner outputs a `Stockpile` object with the following structure:

```json
{
  "name": "Logi",
  "type": "seaport",
  "hex": "Westgate",
  "is_reserve": false,
  "items": [
    {
      "code": "GrenadeLauncherC",
      "quantity": 3,
      "crated": false,
      "confidence": 0.95
    }
  ],
  "timestamp": "2024-01-04T09:00:00",
  "resolution": "1920x1080",
  "shard": "ABLE"
}
```

Run `fs-ocr schema` for the complete JSON Schema.

## Requirements

- Python 3.12+
- Tesseract OCR with custom `renner_numbers` model
- Template database (HDF5 format)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid input (file not found, malformed image) |
| 3 | Processing failure (OCR ran but failed) |
