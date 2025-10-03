# Foxhole Stockpiles

[![CI](https://github.com/xurxogr/foxhole-stockpiles/workflows/CI/badge.svg)](https://github.com/xurxogr/foxhole-stockpiles/actions)
[![codecov](https://codecov.io/gh/xurxogr/foxhole-stockpiles/branch/main/graph/badge.svg)](https://codecov.io/gh/xurxogr/foxhole-stockpiles)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
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

## What It Does

The project consists of five command-line tools that work together:

1. **Asset Extraction** - Extracts icon assets from Foxhole PAK files
2. **Template Generation** - Creates resolution-specific templates with crate overlays
3. **Database Building** - Compiles templates into optimized binary databases
4. **Scanner Tool** - Analyzes screenshots to detect and identify stockpile items with automatic quantity recognition
5. **Inspector Tool** - Debugs and validates template databases

## Available Command-Line Tools

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

## Requirements

- Python 3.12 or higher
- **Tesseract OCR** - Required for quantity detection from stockpile screenshots
- External tools (Windows-specific):
  - `repak.exe` - For PAK file extraction
  - `umodel.exe` - For asset conversion
- Foxhole game files and `catalog.json`
- Custom Tesseract model for Renner font recognition (see Installation section)

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

# Install with development dependencies
pip install -e .[dev]

# Install everything (server + dev)
pip install -e .[server,dev]
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

The stockpile scanner uses a custom-trained Tesseract model optimized for recognizing the Renner font used in Foxhole's UI. **This model is already included in the repository** in the `tessdata/` folder.

The directory structure is:
```
foxhole-stockpiles/
├── tessdata/
│   └── custom.traineddata  # Already provided
└── ...
```

The scanner will automatically detect and use this custom model for improved quantity recognition accuracy.

### 5. Set Up Pre-Commit Hooks (Optional, for Development)

```bash
pre-commit install
```

## Usage Workflow

### Complete Pipeline

1. **Extract assets from game PAK files:**
```bash
fs extract-assets \
  --catalog catalog.json \
  --pak "C:/Program Files (x86)/Steam/steamapps/common/Foxhole/War/Content/Paks/War-WindowsNoEditor.pak" \
  --output raw_assets/
```

2. **Generate resolution-specific templates:**
```bash
fs generate-templates \
  --catalog catalog.json \
  --assets raw_assets/ \
  --templates processed_templates/
```

3. **Build optimized binary database:**
```bash
fs database-builder \
  --catalog catalog.json \
  --templates processed_templates/ \
  --database foxhole_templates.pkl
```

4. **Scan a stockpile screenshot:**
```bash
fs scanner \
  --database foxhole_templates.pkl \
  --image your_screenshot.png
```

The scanner will automatically:
- Detect and identify all items in the stockpile
- Extract quantities using OCR with the custom Renner font model
- Output structured JSON data with items, quantities, and metadata

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

For more details, see the [API Server Documentation](foxhole_stockpiles/commands/api_server/README.md) and [API Usage Guide](docs/api-usage.md).

### Docker Deployment

The easiest way to run the API server is using Docker:

```bash
# Build the image
docker build -t foxhole-stockpiles .

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

The Docker image includes:
- Python 3.12 runtime
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

- [Asset Extractor](foxhole_stockpiles/commands/uasset_extractor/README.md) - Extract icons from PAK files
- [Template Generator](foxhole_stockpiles/commands/generate_templates/README.md) - Generate resolution-specific templates
- [Database Builder](foxhole_stockpiles/commands/database_builder/README.md) - Build optimized template databases
- [Scanner](foxhole_stockpiles/commands/stockpile_scanner/README.md) - Analyze stockpile screenshots
- [Inspector](foxhole_stockpiles/commands/candidate_inspector/README.md) - Debug and validate databases
- [API Server](foxhole_stockpiles/commands/api_server/README.md) - HTTP API server

### Guides

- [Configuration Guide](docs/configuration.md) - Environment variables and settings
- [API Usage](docs/api-usage.md) - HTTP API endpoints and examples
- [Docker Deployment](docs/docker.md) - Docker and docker-compose setup
- [API Authentication](docs/api-authentication.md) - Authentication configuration
- [Webhook Integration](docs/webhooks.md) - Webhook setup and usage
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Credits

This project was heavily influenced by the [FIR (Foxhole Item Recognition)](https://github.com/GICodeWarrior/fir) project:
- **catalog.json**: Directly copied from FIR project
- **Conceptual approach**: Image generation from PAK extraction inspired by FIR

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.
