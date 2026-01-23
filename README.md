# Foxhole Stockpiles

[![CI](https://github.com/xurxogr/foxhole-stockpiles/workflows/CI/badge.svg)](https://github.com/xurxogr/foxhole-stockpiles/actions)
[![codecov](https://codecov.io/gh/xurxogr/foxhole-stockpiles/branch/main/graph/badge.svg)](https://codecov.io/gh/xurxogr/foxhole-stockpiles)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A command-line toolset for processing Foxhole game screenshots to automatically extract stockpile information from game assets.

## Current Implementation Status

This project provides a complete pipeline for extracting game assets and building template databases for stockpile recognition, along with a scanner tool to analyze screenshots.

## Why This Tool Exists

Extracting Foxhole stockpile information by hand is slow, error-prone, and difficult to scale.
This tool automates that process by converting screenshots into structured, machine-readable data, enabling you to:

- Quickly identify and count stockpile items
- Output results as JSON for automation and tracking
- Integrate directly into scripts or larger data-processing pipelines

The system is designed for flexibility, supporting multiple resolutions and easy database rebuilding when new game content is released.

## Performance & Accuracy

Based on analysis of 1,000+ production scans:

### Detection Accuracy
- **99.99% detection rate** - Only 4 undetected items out of 27,538 scanned
- **97.89% average OCR confidence** - High-quality text recognition
- **Near-perfect matching** - Works reliably across all supported resolutions

### Speed
- **1-2 seconds** per screenshot on modern consumer CPUs (6+ cores)
- **3-4 seconds** on server-grade hardware (AMD EPYC 6-core)
- **Concurrent processing** - Handles multiple scans simultaneously via API server
- **Performance scales with CPU** - More cores = faster processing

### Memory Efficiency
- **~200 MB baseline** - Idle memory usage with cached templates
- **~400 MB peak** - During active concurrent scanning
- **Automatic cleanup** after each scan (gc.collect + malloc_trim)
- **LRU cache** for template databases with configurable size
- **Production-ready** memory management with jemalloc

### Supported Resolutions
Optimized for all common gaming resolutions with consistent accuracy:
- 1920x1080 (most tested) - 98.32% confidence, 99.99% detection rate
- 1920x1200, 2560x1440, 3840x2160 (4K)
- 1600x1200, 1600x900, 1280x1024

**Note:** Performance varies with CPU speed and available cores. The scanner uses OpenCV and Tesseract (C libraries) which benefit significantly from multi-core processors.

## What It Does

The project provides a comprehensive toolkit for Foxhole stockpile recognition:

**Core Pipeline Tools:**
1. **Asset Extraction** - Extracts icon assets from Foxhole PAK files
2. **Template Generation** - Creates resolution-specific templates with crate overlays
3. **Database Building** - Compiles templates into optimized binary databases
4. **Scanner Tool** - Analyzes screenshots to detect and identify stockpile items with automatic quantity recognition

**Additional Tools:**
5. **Inspector Tool** - Debugs and validates template databases
6. **API Server** - HTTP REST API for processing screenshots
7. **GUI Application** - User-friendly graphical interface for configuration and scanning
8. **Database Management** - Tools for adding icons and migrating database formats
9. **Configuration Management** - Tools for updating configuration files

For technical details on the system design and implementation decisions, see the [Architecture Documentation](docs/architecture.md).

## Available Command-Line Tools

### fs catalog-builder
Builds catalog.json from Foxhole PAK files by extracting game blueprints, converting them to JSON, and parsing item definitions. Generates the complete item catalog automatically without manual data entry.

### fs extract-assets
Extracts icon assets from Foxhole PAK files and converts them to PNG format.

### fs generate-templates
Generates resolution-specific template variants from extracted assets with proper scaling and crate overlays.

### fs database-builder
Compiles processed templates into optimized binary databases for fast runtime loading.

### fs scanner
Analyzes Foxhole stockpile screenshots to detect items and quantities using the compiled database. Automatically detects item quantities using OCR with a custom-trained Tesseract model optimized for Foxhole's Renner font.

### fs inspect
Debugging tool for inspecting database contents and testing icon recognition.

### fs server
Starts the FastAPI server for processing screenshots via HTTP API.

### fs add-icon
Manually adds individual icons to existing template databases without rebuilding the entire database.

### fs add-mod
Adds all icons from a mod's PAK file(s) to the template database in one command. Runs the complete pipeline: extracting assets, generating templates, and merging into the database.

### fs update-db
Migrates template databases to the latest format version with automatic sequential migration (v1→v2→v3). Converts legacy pickle databases to HDF5 format for better memory efficiency and faster loading.

### fs update-config
Updates `.fs_config` configuration files to the latest format version with automatic migration.

### fs gui / fs-gui
Launches the PyQt6 graphical user interface for managing configurations and running scans. Provides a user-friendly interface for non-technical users.

- `fs gui` - Launches GUI via CLI dispatcher
- `fs-gui` - Direct GUI launcher (no console window on Windows, recommended for building standalone executables)

## Requirements

- Python 3.12 or higher
- **Tesseract OCR** - Required for quantity detection from stockpile screenshots
- Custom Tesseract model for Renner font recognition (included in repository)

### For Scanner Only

- **Pre-built template database** - Download `foxhole_templates.pkl` from database releases (tags starting with `db-`)
  - See [Releases](https://github.com/xurxogr/foxhole-stockpiles/releases) and look for database releases matching your Foxhole game version
- **Item catalog** (`data/catalog.json`) - Included in repository

### For Custom Database Building (Optional)

- External tools (Windows-specific):
  - `repak.exe` - For PAK file extraction
  - `umodel.exe` - For asset conversion
- Foxhole game PAK files (from your game installation)
- Mod PAK files (if using custom mods)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/xurxogr/foxhole-stockpiles.git
cd foxhole-stockpiles
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install the Package

```bash
# Install base package (CLI tools: scanner, database-builder, etc.)
pip install -e .

# Install with API server support (adds fs server command)
pip install -e .[server]

# Install with GUI support (adds fs gui and fs-gui commands)
pip install -e .[gui]

# Install with development dependencies
pip install -e .[dev]

# Install everything (server + gui + dev)
pip install -e .[server,gui,dev]
```

### 4. Install and Configure Tesseract OCR

#### Install Tesseract

**Windows:**
```bash
# Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
# Or using chocolatey:
choco install tesseract
```

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr
```

#### Set Up Custom Renner Font Model

The stockpile scanner uses a custom-trained Tesseract model (`renner_numbers.traineddata`) optimized for recognizing quantities in Foxhole's Renner font. **This model is required for accurate quantity detection and is already included in the repository** in the `tessdata/` folder.

The directory structure is:
```
foxhole-stockpiles/
├── tessdata/
│   └── renner_numbers.traineddata  # Already provided - required for quantity detection
└── ...
```

The scanner automatically uses this custom model for quantity detection. For stockpile names, types, and other text detection, the scanner uses standard Tesseract language models.

#### Install Additional Language Support (Optional)

Foxhole supports multiple languages. If you want to detect stockpile information in languages other than English, you need to install the corresponding Tesseract language data files:

**Supported Languages:**
- English (eng) - Included with Tesseract by default
- Portuguese (por)
- French (fra)
- German (deu)
- Russian (rus)
- Chinese Simplified (chi_sim)

**Installation:**

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr-por tesseract-ocr-fra tesseract-ocr-deu \
                 tesseract-ocr-rus tesseract-ocr-chi-sim
```

**macOS:**
```bash
brew install tesseract-lang
```

**Windows:**
- Download language data files from https://github.com/tesseract-ocr/tessdata
- Place `.traineddata` files in your Tesseract installation's `tessdata` folder
  - Default location: `C:\Program Files\Tesseract-OCR\tessdata\`

**Note:** If you only play Foxhole in English, you don't need to install additional language packs. The scanner will work perfectly with just the English model (included by default) and the bundled `renner_numbers` model for quantity detection.

### 5. Set Up Pre-Commit Hooks (Optional, for Development)

```bash
pre-commit install
```

## Usage Workflow

### Quick Start (Using Pre-built Database)

Download a pre-built template database for vanilla Foxhole items:

1. Go to [Releases](https://github.com/xurxogr/foxhole-stockpiles/releases)
2. Find a database release (tagged as `db-*`) matching your Foxhole game version
3. Download `foxhole_templates.pkl` from the release assets
4. Place it in your working directory or a `data/` folder
5. Run the scanner:

```bash
fs scanner \
  --database foxhole_templates.pkl \
  --image your_screenshot.png
```

Optional filters:
```bash
# Filter by faction
fs scanner --database foxhole_templates.pkl --image screenshot.png --faction colonials
```

The scanner will automatically:
- Detect and identify all items in the stockpile
- Extract quantities using OCR with the custom Renner font model
- Output structured JSON data with items, quantities, and metadata
- Validate mod names against available mods in the database

### Building Custom Database (For Mods or Game Updates)

If you need to include custom mods or rebuild the database for a new game version:

1. **Extract assets from game PAK files:**
```bash
fs extract-assets \
  --catalog data/catalog.json \
  --pak "C:/Program Files (x86)/Steam/steamapps/common/Foxhole/War/Content/Paks/War-WindowsNoEditor.pak" \
  --output raw_assets/
```

2. **Generate resolution-specific templates:**
```bash
fs generate-templates \
  --catalog data/catalog.json \
  --assets raw_assets/ \
  --templates processed_templates/
```

3. **Build optimized binary database:**
```bash
fs database-builder \
  --catalog data/catalog.json \
  --templates processed_templates/ \
  --database data/foxhole_templates.pkl
```

4. **Scan with your custom database:**
```bash
fs scanner \
  --database data/foxhole_templates.pkl \
  --image your_screenshot.png
```

## Core Dependencies

- **Image Processing**: OpenCV (opencv-python), NumPy
- **OCR**: Tesseract OCR with pytesseract Python wrapper
- **Data Handling**: Pydantic v2 for validation
- **Development**: Ruff (linting), MyPy (type checking), Pre-commit hooks

## API Server

The project includes a FastAPI server for processing stockpile screenshots via HTTP.

**Installation:** The API server requires additional dependencies. Install with:
```bash
pip install -e .[server]
```

**Usage:**
```bash
# Start the API server (recommended)
fs server

# Start on custom port
fs server --port 8080

# Start with multiple workers for production
fs server --host 0.0.0.0 --port 8000 --workers 4

# Development mode with auto-reload
fs server --reload --log-level debug
```

The API exposes endpoints for:
- `/ocr/scan_image` - Upload and analyze stockpile screenshots
- `/health` - Health check endpoint

**Configuration:**
Quick start with example configs:
```bash
# Copy minimal config example
cp .fs_config.example .fs_config

# Or use Docker-optimized config
cp docs/examples/fs_config.docker .fs_config
```

For more details, see:
- [Configuration Examples](docs/examples/README.md) - Ready-to-use config files for different scenarios
- [API Server Documentation](foxhole_stockpiles/commands/api_server/README.md)
- [API Usage Guide](docs/api-usage.md)

### Notifications

The API server includes a notification system that can send alerts to Discord channels when stockpile scans occur, server events happen, or errors are encountered.

**Configuration:**

Add notifications to your `.fs_config` or environment variables:

```json
{
  "notifications": {
    "enabled": true,
    "notifiers": [
      {
        "type": "discord",
        "name": "Main Server",
        "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
        "username": "Stockpile Bot",
        "events": [
          "stockpile.scanned",
          "stockpile.scan_failed"
        ],
        "message_templates": {
          "stockpile.scanned": "📦 STOCKPILE_NAME @ SHARD [TIME] - ITEM_COUNT items (UNMATCHED_ITEMS unknown) - AVG_CONFIDENCE confidence"
        }
      },
      {
        "type": "discord",
        "name": "Admin Channel",
        "webhook_url": "https://discord.com/api/webhooks/ADMIN_WEBHOOK_ID/ADMIN_WEBHOOK_TOKEN",
        "username": "Admin Bot",
        "events": [
          "stockpile.scan_failed",
          "server.started",
          "server.stopped"
        ]
      }
    ]
  }
}
```

**Message Templates:**

Customize notification messages using placeholders. If not specified, default templates are used.

Placeholders are replaced with actual values - just use them as-is in your message template.

Available placeholders:
- `STOCKPILE_NAME` - Name of the stockpile
- `STOCKPILE_TYPE` - Type of stockpile (Public, Private, etc.)
- `SHARD` - Shard/server name
- `TIME` - In-game time
- `ITEM_COUNT` - Total number of items
- `MATCHED_ITEMS` - Number of successfully matched items
- `UNMATCHED_ITEMS` - Number of unknown/unmatched items
- `AVG_CONFIDENCE` - Average confidence (formatted as percentage, e.g., "85.6%")
- `DURATION` - Scan duration (formatted as seconds, e.g., "2.34s")
- `RESOLUTION` - Screenshot resolution
- `ERROR` - Error message (for failed events)

Example templates:
```json
"message_templates": {
  "stockpile.scanned": "✅ STOCKPILE_NAME (STOCKPILE_TYPE) - ITEM_COUNT items in DURATION",
  "stockpile.scan_failed": "❌ Scan failed: ERROR",
  "stockpile.scan_started": "🔄 Scanning stockpile...",
  "server.started": "🚀 API server is now online",
  "server.stopped": "🛑 API server is shutting down"
}
```

**Note:** Placeholders are case-sensitive and will be replaced exactly as written. Any text not matching a placeholder will remain unchanged, so typos like `{stockpile_name` won't cause errors.

**Environment Variables:**

```bash
# Enable notifications
FS_NOTIFICATIONS__ENABLED=true

# Configure Discord notifiers (JSON array)
FS_NOTIFICATIONS__NOTIFIERS='[{"type":"discord","name":"Main","webhook_url":"https://discord.com/...","events":["stockpile.scanned"]}]'
```

**Available Event Types:**
- `stockpile.scan_started` - Scan has started
- `stockpile.scanned` - Successful scan with item details
- `stockpile.scan_failed` - Scan failed with error message
- `server.started` - API server started
- `server.stopped` - API server stopped

**Discord Webhook Setup:**
1. In Discord, go to Server Settings → Integrations → Webhooks
2. Click "New Webhook" or "Create Webhook"
3. Set a name and choose the channel
4. Copy the Webhook URL
5. Add the URL to your configuration

**Multiple Notifiers:**
You can configure multiple Discord webhooks to send different events to different channels. For example:
- Main channel: successful scans
- Admin channel: errors and server events
- Dev channel: all events for debugging

### Docker Deployment

The easiest way to run the API server is using Docker:

```bash
# Build the image (Python 3.12 by default)
docker build -t foxhole-stockpiles .

# Build with Python 3.13
docker build --build-arg PYTHON_VERSION=3.13 -t foxhole-stockpiles:py313 .

# Run with docker-compose (recommended)
docker-compose up -d

# Or run directly
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/data:ro \
  -e FS_SCANNER__DATABASE_PATH=/data/foxhole_templates.pkl \
  -e FS_API_AUTH__AUTH_TYPE=bearer \
  -e FS_API_AUTH__AUTH_TOKEN=your-secret-token \
  foxhole-stockpiles
```

**Build Options:**

- `PYTHON_VERSION` - Choose Python version (default: `3.12`, supports: `3.13`)
  ```bash
  docker build --build-arg PYTHON_VERSION=3.13 -t foxhole-stockpiles .
  ```

**Runtime Configuration:**

The Docker image includes **jemalloc** for better memory management (enabled by default). To disable:
```bash
docker run -d -e LD_PRELOAD= foxhole-stockpiles
# Or in docker-compose.yml:
# environment:
#   - LD_PRELOAD=
```

**Memory Optimization:**

The image includes jemalloc which reduces memory fragmentation by ~20-40 MB. Python 3.13 provides an additional ~10-20 MB savings.

The Docker image includes:
- Python 3.12 runtime (or 3.13 via build arg)
- jemalloc for improved memory management
- All required dependencies
- Tesseract OCR
- Non-root user for security
- Health checks
- Multi-stage build for smaller image size

See [docker-compose.yml](docker-compose.yml) for configuration examples.

## Project Structure

```
foxhole_stockpiles/
├── api/               # FastAPI server
│   ├── server.py
│   └── auth.py
├── commands/          # Command-line tools
│   ├── uasset_extractor/
│   ├── generate_templates/
│   ├── database_builder/
│   ├── stockpile_scanner/
│   └── candidate_inspector/
├── core/              # Core utilities
│   ├── logging.py
│   └── utils.py
├── enums/             # Enumeration types
├── models/            # Data models
└── services/          # Service layer
    ├── stockpile_detector.py
    ├── template_database.py
    └── template_manager.py
```

## Development

### Code Quality Tools

The project uses several tools to maintain code quality:

```bash
# Run linter
ruff check foxhole_stockpiles/

# Type checking
mypy foxhole_stockpiles/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Building Windows Executable

For Windows users who want a standalone executable, the project includes a build script:

```bash
# Ensure PyInstaller is installed
pip install pyinstaller

# Run the build script
python build_fs.py
```

This creates a single `fs.exe` file in the `dist/` directory that contains all dependencies and can be used without Python installation:

```bash
# Use the executable with the same command syntax
fs.exe scanner --database templates.pkl --image screenshot.png
fs.exe extract-assets --catalog catalog.json --pak game.pak --output assets/
```

The executable is typically 50-80MB and includes all required dependencies except external tools (repak.exe, umodel.exe) which must still be provided separately.

### Testing

The project includes a comprehensive test suite covering all major components:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=foxhole_stockpiles --cov-report=html

# Run specific test modules
pytest tests/commands/stockpile_scanner/
pytest tests/services/
```

Test coverage includes:
- Command-line tools (asset extraction, template generation, database building, scanner)
- Core services (template matching, OCR processing, stockpile detection)
- Data models and validation
- API server and authentication
- Webhook connectors and output handlers

## Documentation

### Command-Line Tools

Each CLI tool has detailed documentation in its directory:

- [Catalog Builder](foxhole_stockpiles/commands/catalog_builder/README.md) - Build catalog.json from PAK files
- [Asset Extractor](foxhole_stockpiles/commands/uasset_extractor/README.md) - Extract icons from PAK files
- [Template Generator](foxhole_stockpiles/commands/generate_templates/README.md) - Generate resolution-specific templates
- [Database Builder](foxhole_stockpiles/commands/database_builder/README.md) - Build optimized template databases
- [Scanner](foxhole_stockpiles/commands/stockpile_scanner/README.md) - Analyze stockpile screenshots
- [Inspector](foxhole_stockpiles/commands/candidate_inspector/README.md) - Debug and validate databases
- [API Server](foxhole_stockpiles/commands/api_server/README.md) - HTTP API server
- [Add Icon](foxhole_stockpiles/commands/add_icon/README.md) - Add individual icons to databases
- [Add Mod](foxhole_stockpiles/commands/add_mod/README.md) - Add mod icons to databases
- [Update DB](foxhole_stockpiles/commands/update_db/README.md) - Migrate template databases
- [Update Config](foxhole_stockpiles/commands/update_config/README.md) - Migrate configuration files
- [GUI](foxhole_stockpiles/commands/gui/README.md) - Graphical user interface

### Guides

- [Configuration Examples](docs/examples/README.md) - Ready-to-use config files (minimal, Docker, production)
- [Configuration Guide](docs/configuration.md) - Environment variables and settings
- [API Usage](docs/api-usage.md) - HTTP API endpoints and examples
- [Docker Deployment](docs/docker.md) - Docker and docker-compose setup
- [API Authentication](docs/api-authentication.md) - Authentication configuration
- [Webhook Integration](docs/webhooks.md) - Webhook setup and usage
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Credits

This project was inspired by the [FIR (Foxhole Item Recognition)](https://github.com/GICodeWarrior/fir) project:
- **catalog.json**: Used FIR's catalog until we developed our own catalog builder
- **Conceptual approach**: Image generation from PAK extraction inspired by FIR

## License

This project is licensed under the MIT License - see the LICENSE file for details.

**Note**: The included `data/catalog.json` and pre-built template database (available in releases) contain data derived from Foxhole game assets, which are property of [Siege Camp](https://www.siegecamp.com/). These files are made available under Fair Use for personal use. Users are responsible for complying with applicable terms of service.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.
