# GUI Command

Launches the PyQt6 graphical user interface for FS (Foxhole Stockpiles).

## Usage

```bash
fs gui
# or
python -m foxhole_stockpiles.commands.gui
```

### WSL2 Requirements

If running on WSL2, you need to use the XCB platform due to WSLg + Qt6 + Wayland compatibility issues:

```bash
# Install required dependencies
sudo apt-get install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-xkb1

# Run with XCB platform
export QT_QPA_PLATFORM=xcb
fs gui
```

## Current Features

### Main Window

The main window displays the application name, version, and provides access to:

- **File > Configuration**: Opens the configuration helper
- **File > Exit**: Closes the application
- **Help > About**: Shows application information, version, and links to GitHub repositories

### Configuration Helper

Access via **File > Configuration**. Opens as a centered modal dialog with two modes:

#### Basic Configuration Mode (Default)

A simplified interface for non-technical users with essential settings only:

- **Server Settings**
  - Port: API server port (default: 8000)

- **Authentication**
  - Auth Type: None or Basic (HTTP Basic Auth)
  - Username/Password: Shown only when Basic auth is selected

- **Scanner Settings**
  - Database Path: Path to template database (.h5 file)

- **Output Settings**
  - Destination: console (default), return, file, or webhook
  - File Path: Shown when destination is "file"
  - Webhook URL: Shown when destination is "webhook"
  - Webhook Auth: None or Basic with username/password

#### Advanced Configuration Mode

Enable by checking **"Show Advanced Settings"** to access all configuration options across 7 detailed tabs:

1. **API Server**: Host, port, reload, log level
2. **API Authentication**: Auth type and credentials
3. **Scanner**: Database path, cache settings, confidence thresholds, debug options
4. **Output**: Format, destination, file/webhook/console settings with full auth options
5. **OCR**: Layout detection parameters (box dimensions, offsets, thresholds)
6. **Templates**: Template matching settings and cache configuration
7. **Logging**: Log levels, file output, and rotation settings

**Warning**: Some advanced options are critical - misconfiguring them (especially OCR and Templates settings) can break stockpile scanning completely.

### Configuration Validation

All configuration changes are validated before saving:
- Required fields are checked
- Settings consistency is verified
- Invalid configurations are rejected with helpful error messages

### Configuration Storage

Settings are saved to `~/.fs_config` in JSON format and persist between sessions.

## Dependencies

- PyQt6
- Python 3.12+
