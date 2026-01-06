# GUI Command

Launches the PyQt6 graphical user interface for FS (Foxhole Stockpiles).

## Installation

The GUI requires PyQt6. Install with:

```bash
pip install -e .[gui]
```

## Usage

**Recommended:**
```bash
fs gui
```

**Alternative Methods:**
```bash
# Direct GUI launcher (no console on Windows)
fs-gui

# Python module
python -m foxhole_stockpiles.commands.gui
```

### Windows Standalone Executable

The `fs-gui` command is designed for building standalone Windows executables without a console window.

**Using PyInstaller:**
```bash
# Install PyInstaller
pip install pyinstaller

# Build standalone GUI executable (no console)
pyinstaller --windowed --onefile --name="Foxhole-Stockpiles" \
    --add-data "tessdata;tessdata" \
    --add-data "data;data" \
    -m foxhole_stockpiles.gui.app:launch_gui
```

The `--windowed` flag ensures no console window appears when launching the GUI on Windows.

### WSL2 Requirements

If running on WSL2, you need to use the XCB platform due to WSLg + Qt6 + Wayland compatibility issues:

```bash
# Install required dependencies
sudo apt-get install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-xkb1

# Run with XCB platform
export QT_QPA_PLATFORM=xcb
fs gui
```

## Features

### Main Window

The main window provides an integrated interface for running the FastAPI server and scanning screenshots:

#### Server Control Panel

- **Start/Stop Server**: One-click control to start/stop the FastAPI server
- **Server Status**: Real-time display of server status (Running/Stopped)
- **Screenshot Scanning**:
  - Drag & drop screenshots directly onto the drop zone
  - Click to open file dialog for selecting screenshots
  - Automatic scanning when server is running
  - Supports PNG, JPG, and JPEG formats

#### Real-time Logging

- **Colored log display**: Color-coded by severity level (DEBUG, INFO, WARNING, ERROR)
- **Four-column layout**:
  - Timestamp: When the log event occurred
  - Level: Log severity level
  - Module: Which component generated the log
  - Message: The log message content
- **Auto-scroll**: Automatically scrolls to show latest logs
- **Clear logs**: Button to clear all accumulated logs
- **Dark theme**: Console-style dark background for better readability

### Configuration Dialog

Access via **File > Configuration**. Opens as a centered modal dialog.

#### Basic Configuration Mode (Default)

A simplified interface designed for non-technical users with only essential settings:

**Server Settings:**
- Port: API server port (default: 8000)

**Authentication:**
- Auth Type: None or Basic (HTTP Basic Auth)
- Username/Password: Shown only when Basic auth is selected

**Scanner Settings:**
- Database Path: Path to template database (.h5 file) with browse button

**Output Settings:**
- Destination: console (default), return, file, or webhook
- Dynamic sections that appear based on destination:
  - **File**: Path input with browse button
  - **Webhook**: URL and optional Basic authentication

#### Advanced Configuration Mode

Enable by checking **"Show Advanced Settings"** to access all configuration options across detailed tabs:

1. **API Server**:
   - Host and port configuration
   - Reload on code changes (development)
   - Log level selection
   - CORS origins
   - Memory monitoring options

2. **API Authentication**:
   - Auth type selection (none, bearer, basic)
   - Token/credentials management

3. **Scanner**:
   - Database path and cache settings
   - Faction filter options
   - Confidence thresholds
   - Max NCC candidates
   - pHash settings
   - Debug options (save debug images)

4. **Output**:
   - Format (JSON)
   - Destination (return, file, webhook, console)
   - File settings (path with timestamp support)
   - Webhook settings (URL, auth type, token, custom headers)
   - Console settings

5. **OCR**:
   - Layout detection parameters
   - Box dimensions (width, height)
   - Offsets (column, row, group, icon-to-quantity)
   - Title detection (margin, min width, height)
   - Gray threshold values
   - Pixel difference tolerance

6. **Templates**:
   - Template matching settings
   - Crate detection RGB multipliers and offsets
   - Cache configuration

7. **Database Builder**:
   - Repak tool path
   - UModel tool path
   - UAssetGUI tool path
   - Workers count
   - Filter options

8. **Logging**:
   - Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - File output configuration
   - Log format customization
   - Date format
   - Log rotation settings

**⚠️ Warning**: Advanced settings include critical parameters. Misconfiguring OCR or Templates settings can break stockpile scanning completely. Only modify if you understand the implications.

#### Configuration Validation

All configuration changes are validated before saving:
- Required fields are checked
- Settings consistency is verified
- Invalid configurations are rejected with helpful error messages
- Changes are highlighted when modified

#### Configuration Storage

Settings are saved to `~/.fs_config` in JSON format and persist between sessions. The configuration uses versioned format (current: v2) with automatic migration support.

### Database Builder Window

Access via **Database > Build**. Provides a user-friendly interface for building the template database from PAK files.

#### Features

**Vanilla PAK Section (Optional):**
- Browse to select the vanilla Foxhole PAK file
- Automatically extracted if needed for shared resources (crate icon, subicons)
- Clear button to remove selection
- Info message explaining vanilla PAK purpose

**Mod PAK Files Section:**
- Add one or multiple mod PAK files
- Drag & drop support for adding PAK files quickly
- List view showing all selected mod PAKs
- Remove selected or clear all functionality
- Multi-selection support

**Configuration Verification:**
- Checks if Database Builder is properly configured
- Verifies required tools (repak, UModel, UAssetGUI) are configured
- Shows warning and disables UI if configuration is incomplete
- Helpful error messages directing users to configuration dialog

**Import Process:**
- Real-time logging during import process
- Shows extraction progress
- Displays conversion status
- Reports success/failure for each step
- Color-coded log messages for easy status tracking

**Keyboard Shortcuts:**
- `Escape`: Close window
- `Delete`: Remove selected PAK files from list

**Import Log Display:**
- Four-column table layout (Time, Level, Module, Message)
- Color-coded by severity
- Auto-scroll to latest messages
- Dark theme for better readability
- Clear logs button

### Menu Bar

**File Menu:**
- **Configuration...**: Opens the configuration dialog
- **Minimize to Tray on Close**: Toggle whether closing the window minimizes to system tray (unchecked by default)
- **Exit**: Quits the application completely

**Database Menu:**
- **Build...**: Opens the database builder window for creating/updating template databases from PAK files

**Help Menu:**
- **About**: Shows application information including:
  - Application version
  - Feature list
  - Links to GitHub repositories (main project and FS Client)
  - Copyright and license information

### System Tray

The application supports system tray for background operation (opt-in):

**Enabling System Tray:**
- Check "File > Minimize to Tray on Close" to enable
- Once enabled, clicking the window close button (X) minimizes to tray instead of quitting
- The tray icon will always be visible when the application is running

**Features:**
- **Auto-minimize**: When enabled, clicking the close button minimizes to tray instead of quitting
- **Tray icon**: Displays in system tray with tooltip showing application version
- **Notification**: Shows a balloon notification on first minimize to inform user

**Tray Menu** (right-click on tray icon):
- **Show**: Restore and show the main window
- **Hide**: Hide the main window to tray
- **Configuration...**: Open configuration dialog
- **Quit**: Completely exit the application

**Double-click**: Double-clicking the tray icon restores the main window

**Note**: By default, the close button quits the application. Check "File > Minimize to Tray on Close" to enable minimize-to-tray behavior.

## Workflow Examples

### First-Time Setup

1. Launch GUI: `fs gui`
2. Open Configuration (File > Configuration)
3. Set database path to your template database file
4. Configure server port if needed (default: 8000)
5. Save configuration
6. Start the server
7. Drop screenshots to scan them

### Building Custom Database

1. Open Database Builder window (Database > Build)
2. If configuration warning appears:
   - Click "Open Configuration" to set up Database Builder settings
   - Configure paths for repak, UModel, and UAssetGUI tools
   - Save and return to Database Builder window
3. (Optional) Select vanilla PAK file if needed
4. Add mod PAK file(s) via Browse or drag & drop
5. Click "Start Import"
6. Monitor progress in the log display
7. Wait for completion message

### Advanced Configuration

1. Open Configuration (File > Configuration)
2. Check "Show Advanced Settings"
3. Navigate through tabs to configure specific features:
   - Adjust OCR parameters for better text detection
   - Configure template matching thresholds
   - Set up webhook notifications
   - Enable debug image output
4. Save configuration
5. Restart server if it's running for changes to take effect

## Technical Details

### Dependencies

- PyQt6 >= 6.6.0
- Python 3.12+
- All core Foxhole Stockpiles dependencies

### Platform Support

- **Windows**: Fully supported
- **Linux**: Supported with standard X11 or Wayland
- **WSL2**: Supported with XCB platform (see WSL2 Requirements above)
- **macOS**: Should work but not extensively tested

### Threading Model

- Server runs in separate thread (non-blocking UI)
- Screenshot scanning runs in background workers
- Icon import runs in background worker thread
- Qt log handler uses signals for thread-safe logging
- All long-running operations are non-blocking

### Configuration Management

- Automatic loading from `~/.fs_config`
- Validation before saving
- Support for both basic and advanced modes
- Automatic migration from older config versions
- Environment variable precedence respected

## Troubleshooting

### GUI Won't Start

**Error: `No module named 'PyQt6'`**
```bash
pip install -e .[gui]
```

**WSL2 Display Issues:**
```bash
export QT_QPA_PLATFORM=xcb
fs gui
```

### Server Won't Start

- Check that port 8000 (or configured port) is not in use
- Verify database path is correct in configuration
- Check logs in the log display for specific errors
- Ensure all required dependencies are installed

### Screenshot Scanning Not Working

- Verify server is running (status shows "Running")
- Check database path is valid in configuration
- Ensure screenshot format is supported (PNG, JPG, JPEG)
- Review logs for specific error messages

### Database Builder Fails

- Verify Database Builder configuration is complete
- Check that repak, UModel, and UAssetGUI paths are correct
- Ensure PAK files are valid Foxhole PAK files
- Review import logs for specific errors
- Check that tools are executable (Windows: .exe files)

### Configuration Changes Not Taking Effect

- Click "Save" or "Apply" button in configuration dialog
- Restart server after configuration changes
- Check for validation errors in status bar
- Verify no environment variables are overriding file settings

### System Tray Not Working

**No tray icon appears:**
- Some desktop environments don't support system tray (e.g., GNOME without extensions)
- On Linux, install a system tray extension if needed
- The application will automatically disable tray functionality if unsupported
- Check logs for "System tray is not available" warning

**Can't find minimized application:**
- **Windows**: Look in the system tray (bottom-right corner)
  - The icon might be in the **overflow area** - click the **^ (up arrow)** in the system tray to see hidden icons
  - You can drag the FS icon from the overflow to the main tray area to keep it visible
- **Linux/Mac**: Look in the top-right corner of the screen
- Right-click the tray icon and select "Show" to restore
- Double-click the tray icon to restore
- If tray icon is still missing, check the application logs for warnings

**Want to disable minimize to tray:**
- Uncheck "File > Minimize to Tray on Close" in the menu
- Close button will then quit the application normally

## Related Documentation

- [Configuration Guide](../../../docs/configuration.md) - Detailed configuration reference
- [API Server Command](../api_server/README.md) - Server command-line options
- [Scanner Command](../stockpile_scanner/README.md) - Scanner details
- [Database Builder Command](../database_builder/README.md) - Database creation
