# GUI Command

Launches the PyQt6 graphical user interface for FS (Foxhole Stockpiles).

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
  - Button is automatically disabled when configuration is invalid
  - Enabled only when database is properly configured and accessible
- **Server Status**: Real-time display of server status (Running/Stopped)
- **Database Information**: Shows loaded database filename and mods when valid
  - Displays relative path if database is in the current directory
  - Shows comma-separated list of available mods

#### Configuration Validation

The main window validates your configuration on startup and after changes:

**When configuration is invalid:**
- Start Server button is disabled
- Error panel replaces the logging display with detailed messages:
  - "⚙️ No Configuration Found" - No config file exists yet
  - "⚙️ Configuration Incomplete" - Database path not configured
  - "⚠️ Database File Not Found" - Configured database doesn't exist
  - "⚠️ Database Error" - Database file is corrupted or invalid
- Database info is hidden

**When configuration is valid:**
- Start Server button is enabled
- Database info shows: "Database: [path] | Mods: [mod1, mod2, ...]"
- Real-time logging panel is displayed

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
- **Conditional display**: Only shown when configuration is valid

### Configuration Dialog

Access via **File > Configuration**. Opens as a centered modal dialog.

#### Configuration Levels

The configuration dialog uses a tiered system to avoid overwhelming users with advanced options. The configuration level can be changed in the **GUI** tab:

- **Basic** (default): Essential settings only - API Server, Scanner, Output, Logging, and GUI tabs
- **Advanced**: Adds Stockpile Types, Notifications, External Tools, and Database Builder tabs
- **Developer**: Full access including OCR and Templates tabs for fine-tuning recognition parameters

#### Configuration Tabs

Tabs are organized by configuration level. Some tabs are always visible, others appear only at Advanced or Developer levels.

**Always Visible:**

1. **API Server**:
   - Host and port configuration
   - Workers count
   - CORS origins (Advanced+)
   - Memory monitoring options
   - Web icon mod
   - **Authentication**:
     - Auth type selection (none, bearer, basic)
     - Username/password for basic auth
     - Token for bearer auth

2. **Scanner**:
   - Database path and cache settings
   - Faction filter options
   - Confidence thresholds
   - Max NCC candidates
   - pHash settings
   - Debug options (save debug images)

3. **Output**:
   - Format (JSON)
   - Destination (return, file, webhook, console)
   - File settings (path with timestamp support)
   - Webhook settings (URL, auth type, token, custom headers)
   - Console settings

4. **Logging**:
   - Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - File output configuration
   - Log format customization
   - Date format
   - Log rotation settings

5. **GUI**:
   - Configuration Level selector (Basic/Advanced/Developer)
   - Minimize to Tray on Close checkbox
   - Language selection for interface localization

**Advanced Level (and above):**

6. **Stockpile Types**:
   - Custom aliases for stockpile type names to handle OCR variations
   - Useful when OCR misreads stockpile names (e.g., "Seaport" detected as "seapon")
   - Built-in translations for all supported languages are already included

7. **Notifications**:
   - Discord webhook integration for event notifications
   - Configure notifiers for events: stockpile.scanned, stockpile.scan_failed, stockpile.scan_started, server.started, server.stopped
   - Custom message templates with placeholders
   - Multiple notifier support

8. **External Tools**:
   - Extractor tool (repak) path - for PAK extraction
   - Converter tool (umodel) path - for UAsset to PNG conversion
   - JSON Converter (UAssetGUI) path - for UAsset to JSON conversion

9. **Database Builder**:
   - Catalog file path
   - Workers count (0 = auto-detect, 1-N for specific count)
   - Target resolutions selection

**Developer Level Only:**

10. **OCR**:
    - Layout detection parameters
    - Box dimensions (width, height)
    - Offsets (column, row, group, icon-to-quantity)
    - Title detection (margin, min width, height)
    - Gray threshold values
    - Pixel difference tolerance

11. **Templates**:
    - Template matching settings
    - Crate detection RGB multipliers and offsets
    - Cache configuration

**⚠️ Warning**: OCR and Templates settings are critical parameters. Misconfiguring them can break stockpile scanning completely. Only modify if you understand the implications.

#### Configuration Validation

All configuration changes are validated before saving:
- Required fields are checked
- Settings consistency is verified
- Invalid configurations are rejected with helpful error messages
- Changes are highlighted when modified

#### Configuration Storage

Settings are saved to `~/.fs_config` in JSON format and persist between sessions. The configuration uses versioned format (current: v5) with automatic migration support.

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

**Configuration Section:**
- **Mod Name**: Identifier for the mod in the database (alphanumeric, spaces, underscores, hyphens)
- **Overwrite existing data**: When checked, replaces existing templates for this mod
- **Destination Database**: Path to the output database file (.h5)
  - Pre-filled from scanner settings if configured
  - Browse button to select a different location
  - Creates new database if file doesn't exist
- **Workers**: Number of parallel processes for database building
  - Default from database_builder.workers setting or detected CPU count
  - Set to 1 to disable multiprocessing (single-threaded)

**Configuration Verification:**
- Checks if Database Builder is properly configured
- Verifies required tools (repak, umodel) are configured in External Tools tab
- Verifies catalog.json path is configured
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

Some menu items are only visible at Advanced or Developer configuration levels.

**File Menu:**
- **Configuration...**: Opens the configuration dialog
- **Scan Screenshot...**: Opens file dialog to select and scan a screenshot
  - Requires server to be running
  - Supports PNG, JPG, and JPEG formats
- **Build Catalog...** *(Advanced+)*: Opens the catalog builder window for generating item catalogs from PAK files
  - Rarely needed - most users download pre-built catalogs
  - Requires External Tools configuration (repak, UAssetGUI)
- **Exit**: Quits the application completely

**Database Menu:**
- **Build...** *(Advanced+)*: Opens the database builder window for creating/updating template databases from PAK files
- **Visualizer...** *(Advanced+)*: Opens the database visualizer for browsing template contents
  - Filter templates by category, faction, and resolution
  - Visual preview of template images
  - Useful for debugging and exploring database contents
- **Information...**: Opens database information window
  - Automatically loads the configured database if available
  - Browse and select any database file (.h5)
  - Statistics load automatically when selecting a file
  - View detailed statistics in table format
  - Shows mod names and template counts per resolution (crated + not crated)
  - Useful for inspecting database contents before using

**Help Menu:**
- **About**: Shows application information including:
  - Application version
  - Feature list
  - Links to GitHub repositories (main project and FS Client)
  - Copyright and license information

### System Tray

The application supports system tray for background operation (opt-in):

**Enabling System Tray:**
- Open Configuration (File > Configuration) and go to the **GUI** tab
- Check "Minimize to Tray on Close" to enable
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

**Note**: By default, the close button quits the application. Enable "Minimize to Tray on Close" in the GUI tab of Configuration to change this behavior.

## Workflow Examples

### First-Time Setup

1. Launch GUI: `fs gui`
   - You'll see an error panel indicating configuration is needed
   - Start Server button will be disabled
2. Open Configuration (File > Configuration)
3. Set database path to your template database file
4. Configure server port if needed (default: 8000)
5. Save configuration
6. The main window will automatically validate and show:
   - Database info with loaded mods
   - Logging panel
   - Enabled Start Server button
7. Start the server
8. Scan screenshots via File > Scan Screenshot...

### Building Custom Database

1. Open Database Builder window (Database > Build)
2. If configuration warning appears:
   - Click "Open Configuration" to set up settings
   - Go to External Tools tab: configure paths for repak (extractor) and umodel (converter)
   - Go to Database Builder tab: configure catalog.json path and workers count
   - Save and return to Database Builder window
3. (Optional) Select vanilla PAK file if needed
4. Add mod PAK file(s) via Browse or drag & drop
5. (Optional) Adjust workers count if needed (lower for stability, higher for speed)
6. Click "Start Import"
7. Monitor progress in the log display
8. Wait for completion message

### Inspecting Database Contents

1. Open Database Information window (Database > Information)
   - If you have a database configured, it will load automatically
   - Otherwise, you'll see a "No database loaded" message
2. (Optional) Click "Browse..." to select a different database file (.h5)
   - Statistics load automatically when you select a file
3. View the statistics table showing:
   - Each mod name in rows
   - Template counts per resolution in columns (e.g., "1080p", "2160p")
   - Numbers represent total templates (crated + not crated versions)
4. Use this to verify database contents before configuring it for use

### Advanced Configuration

1. Open Configuration (File > Configuration)
2. Go to the **GUI** tab and change Configuration Level to **Advanced** or **Developer**
3. Navigate through the newly visible tabs to configure specific features:
   - **Notifications**: Set up Discord webhook notifications
   - **Stockpile Types**: Add custom aliases for OCR variations
   - **External Tools**: Configure paths for repak, umodel, UAssetGUI
   - **Database Builder**: Configure catalog path and workers
   - **OCR** *(Developer only)*: Adjust layout detection parameters
   - **Templates** *(Developer only)*: Configure template matching thresholds
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
- Three configuration levels (Basic, Advanced, Developer)
- Automatic migration from older config versions
- Environment variable precedence respected

## Troubleshooting

### GUI Won't Start

**Error: `No module named 'PyQt6'`**
```bash
# Reinstall the package
pip install -e .
```

**WSL2 Display Issues:**
```bash
export QT_QPA_PLATFORM=xcb
fs gui
```

### Start Server Button Disabled

**Error panel shows configuration/database errors:**
- "⚙️ No Configuration Found" - Run File > Configuration and save settings
- "⚙️ Configuration Incomplete" - Set database path in File > Configuration
- "⚠️ Database File Not Found" - Verify database path exists or build a new database
- "⚠️ Database Error" - Database file may be corrupted, check error details in the message

The Start Server button will automatically enable once configuration is valid.

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
- Use File > Scan Screenshot to manually select files

### Database Builder Fails

- Verify External Tools configuration is complete (repak, umodel paths)
- Verify Database Builder configuration (catalog.json path)
- Check that repak and umodel paths are correct in External Tools tab
- Verify catalog.json file exists and is valid
- Ensure PAK files are valid Foxhole PAK files
- Review import logs for specific errors
- Check that tools are executable (Windows: .exe files)
- Try setting workers to 1 if multiprocessing causes issues

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
- Open Configuration (File > Configuration), go to the **GUI** tab
- Uncheck "Minimize to Tray on Close"
- Close button will then quit the application normally

## Related Documentation

- [Configuration Guide](../../../docs/configuration.md) - Detailed configuration reference
- [API Server Command](../api_server/README.md) - Server command-line options
- [Scanner Command](../stockpile_scanner/README.md) - Scanner details
- [Database Builder Command](../database_builder/README.md) - Database creation
