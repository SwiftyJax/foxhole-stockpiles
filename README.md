# Foxhole Stockpiles

A REST API service that processes Foxhole game screenshots to automatically extract stockpile information and return structured data.

## Why This Tool Exists

This project was created to address limitations in existing Foxhole stockpile analysis tools:

- **Foxhole Stockpiler**: Difficult to get working properly due to monolithic single-file architecture
- **FIR (Foxhole Item Recognition)**: Excellent JavaScript implementation, but didn't provide the JSON output format needed for integration
- **Need for centralized deployment**: Existing tools required local installation and setup on each client machine

This tool enables a **client-server architecture** where:
- **Clients** simply take screenshots and send them via HTTP requests
- **Server** handles all OCR processing and returns structured JSON data
- **Backend integration** (optional) can receive JSON output to track stockpile status across multiple locations

This approach eliminates the need for clients to install OCR dependencies, manage models, or understand image processing - they just send screenshots.

This tool has been successfully used in production for over a year. This repository represents a complete rewrite with modern Python practices, better architecture, and without heavy dependencies like Keras models.

## What It Does

This service analyzes screenshots of stockpiles from the game Foxhole and extracts:
- Stockpile name and type
- All items with their quantities
- Whether items are crated or not
- Structured JSON output for easy integration

The system is designed to handle multiple screen resolutions and support both vanilla game content and popular mods.

## Requirements

- Python 3.12 or higher
- A Foxhole game screenshot containing a stockpile view

## Development Setup

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

### 3. Install Dependencies

```bash
# Install the package in development mode with dev dependencies
pip install -e .[dev]

# Set up pre-commit hooks (for code quality)
pre-commit install
```

### 4. Verify Installation

```bash
# Check that everything is installed correctly
python -c "import foxhole_stockpiles; print('Installation successful!')"
```

## Running the Application

### Development Server

```bash
# Start the development server
python -m foxhole_stockpiles

# The API will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

### Production Server

```bash
# Install production dependencies only
pip install foxhole-stockpiles

# Run with production server
uvicorn foxhole_stockpiles.main:app --host 0.0.0.0 --port 8000
```

## Usage

Send a POST request to `/scan` with a Foxhole stockpile screenshot:

```bash
curl -X POST "http://localhost:8000/scan" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_stockpile_screenshot.png"
```

The response will be a JSON object containing the extracted stockpile data.

## Database Setup

The system requires a pre-built template database for image recognition. See [`commands/README.md`](commands/README.md) for detailed instructions on:

- Extracting assets from Foxhole PAK files
- Building the recognition database
- Supporting mods and custom content
- Troubleshooting extraction issues

## Development

### Code Quality

This project uses several tools to maintain code quality:
- **Ruff**: Fast linting and import sorting
- **MyPy**: Type checking
- **Pre-commit**: Automated quality checks

All code is automatically checked when you commit. To run checks manually:

```bash
# Format code
black foxhole_stockpiles/

# Run linter
ruff check foxhole_stockpiles/

# Type checking
mypy foxhole_stockpiles/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=foxhole_stockpiles
```

## Project Status

🚧 **This project is currently in early development** 🚧

Core features being implemented:
- [ ] Screenshot processing pipeline
- [ ] Icon recognition system
- [ ] Text extraction (quantities, names)
- [ ] REST API endpoints
- [ ] Multi-resolution support
- [ ] Mod compatibility

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the quality checks (`pre-commit run --all-files`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Credits

This project was heavily influenced by the [FIR (Foxhole Item Recognition)](https://github.com/GICodeWarrior/fir) project:
- **catalog.json**: Directly copied from FIR project
- **Conceptual approach**: Image generation from PAK extraction inspired by FIR

This Python implementation represents an independent reimplementation of the core concepts, tailored for REST API deployment and extended functionality.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.
