# Troubleshooting Guide

Common issues and solutions for the Foxhole Stockpile Scanner.

## Installation Issues

### Python Version Error

**Problem:**
```
ERROR: This package requires Python 3.12 or higher
```

**Solution:**
Check your Python version and upgrade if needed:
```bash
python --version  # Should be 3.12 or higher

# On Ubuntu/Debian
sudo apt update
sudo apt install python3.12

# On macOS with Homebrew
brew install python@3.12
```

### Tesseract Not Found

**Problem:**
```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```

**Solution:**
Install Tesseract OCR:

**Windows:**
```bash
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Or use chocolatey:
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

Verify installation:
```bash
tesseract --version
```

### Custom Tesseract Model Not Loading

**Problem:**
Scanner uses default Tesseract model instead of custom Renner font model.

**Solution:**
Verify the custom model exists:
```bash
ls tessdata/custom.traineddata
```

The scanner automatically detects the `tessdata/` directory in the project root.

## Scanner Issues

### Database Not Found

**Problem:**
```
FileNotFoundError: Database file not found: foxhole_templates.h5
```

**Solution:**
1. Build the database first:
   ```bash
   fs-tools build-db \
     --catalog catalog.json \
     --templates processed_templates/ \
     --database foxhole_templates.h5
   ```

2. Or specify the correct path:
   ```bash
   fs scan --database /path/to/database.h5 --image screenshot.png
   ```

3. Or set via environment variable:
   ```bash
   export FS_SCANNER__DATABASE_PATH=/path/to/database.h5
   ```

### No Items Detected

**Problem:**
Scanner completes but finds 0 items in the screenshot.

**Possible Causes & Solutions:**

1. **Wrong resolution database**
   - Verify your screenshot resolution matches the database
   - Check database resolutions: `fs-tools inspect --database templates.h5 --resolution 1080`
   - Rebuild database with correct resolution

2. **Screenshot quality**
   - Use native game resolution screenshots (1080p, 1440p, 2160p)
   - Avoid compressed or scaled images
   - Use PNG format (lossless compression)

3. **Incorrect screenshot type**
   - Scanner expects stockpile inventory screenshots
   - Screenshot must show the stockpile grid with items
   - Title bar must be visible

4. **Resolution mismatch**
   - Matching is most accurate when the screenshot resolution matches a template resolution
   - Use a standard, unscaled screenshot (no display scaling / cropping)
   - The pHash/NCC matching thresholds are fixed defaults as of config v8 and are no longer user-tunable

5. **Debug the detection**
   ```bash
   export FS_SCANNER__DEBUG_MODE=true
   export FS_SCANNER__EXTRACT_ICONS=true
   export FS_LOGGING__LOG_LEVEL=DEBUG
   fs scan --database templates.h5 --image screenshot.png
   ```
   Debug images are written to the `icons/` folder for inspection.

### Some Items Not Detected

**Problem:**
Scanner detects most items but misses some specific ones.

**Solution:**

1. **Check confidence scores in output**
   - Look for warnings in debug logs about low-confidence detections
   - Check the `errors` field in the output for "No match found" messages

2. **Verify the item exists in database**
   ```bash
   fs-tools inspect --database templates.h5 --resolution 1080 --code ItemCode --print
   ```

3. **Screenshot quality issues**
   - Ensure the screenshot resolution matches a database resolution
   - Avoid screenshots with compression artifacts
   - Make sure items are fully visible (not cut off)

4. **Resolution mismatch**
   - The scanner performs best when screenshot resolution exactly matches a database resolution
   - Supported resolutions: 720p, 1080p, 1440p, 2160p
   - Check what resolutions are in your database:
     ```bash
     # List database info with any valid resolution
     fs-tools inspect --database templates.h5 --resolution 1080
     ```

**Note:** The pHash and NCC matching thresholds are fixed defaults as of config v8 and
are no longer user-tunable. If items are consistently missed, the most common fixes are
using a screenshot at a supported resolution and rebuilding the database for the correct
mod version.

See [Configuration Guide](configuration.md) for details on scanner settings.

### Diagnosing Unknown Items

**Problem:**
Some items in the scan result show as `"code": "Unknown"` with `"confidence": 0.0`.

**Understanding the Matching Pipeline:**

The scanner uses a two-phase matching process:
1. **pHash pre-filtering** - Fast perceptual hash comparison filters candidates by Hamming distance (default threshold: 12)
2. **NCC matching** - Normalized Cross-Correlation on remaining candidates finds the best match

An item becomes "Unknown" when:
- No candidates pass the pHash filter, OR
- The item doesn't exist in the database for the detected category/crated status

**Step-by-Step Diagnosis:**

1. **Check the errors field in the output**
   ```bash
   fs scan --image screenshot.png --output-destination return 2>&1 | grep -A5 '"errors"'
   ```

   Look for messages like:
   ```
   "Group 1, index 64: No match found. Quantity: 21, crated: True. Best match: MGTW (crated) (confidence: 0.620)"
   ```

   This tells you:
   - The icon position (group 1, index 64)
   - The quantity detected (21)
   - Whether it's crated (True)
   - The best candidate found and its confidence score

2. **Enable icon extraction for debugging**
   ```bash
   export FS_SCANNER__EXTRACT_ICONS=true
   fs scan --image screenshot.png
   ```

   This saves detected icons to an `icons/` folder as `<index>_<code>.png` so you can visually inspect what was detected.

3. **Use the candidate inspector**
   ```bash
   fs-tools inspect --database templates.h5 --resolution 1080 --icon icons/64_Unknown.png --top 10
   ```

   This shows the top matching candidates with their confidence scores. Replace `1080` with your screenshot's vertical resolution.

4. **Check if the item exists in the database**
   ```bash
   fs-tools inspect --database templates.h5 --resolution 1080 --code MGTW --print
   ```

   Verify the item exists with the correct crated status and mod.

**Common Causes and Solutions:**

| Cause | Symptom | Solution |
|-------|---------|----------|
| Resolution mismatch | Best match has confidence > 0.5 but item still Unknown | Use a screenshot whose resolution matches a database resolution (no display scaling) |
| Mod version mismatch | Item exists but pixels differ | Rebuild database with current mod version |
| Item not in database | No best match found | Add the item using `fs-tools add-icon` or rebuild database |
| Wrong category detected | Match found but wrong category | Check if screenshot has UI artifacts |
| Compression artifacts | Low confidence across all candidates | Use uncompressed PNG screenshots |

**Example: Inspecting a Low-Confidence Match**

If the error shows a best match with decent confidence (e.g., 0.62) but the item is still Unknown:

```bash
# Check matching candidates (use your screenshot's resolution)
fs-tools inspect --database templates.h5 --resolution 1080 --icon icons/64_Unknown.png --top 5
```

If the correct item appears only with low confidence, the screenshot likely doesn't match a
database resolution, or the database is built for a different mod version — rebuild the database
for the relevant mod rather than adjusting matching thresholds (which are fixed as of config v8).

**Example: Mod Version Mismatch**

If you're using a mod (e.g., clean-icons) and items show as Unknown:

```bash
# Verify mod templates exist
fs-tools inspect --database templates.h5 --resolution 1080 --code MGTW --mod clean-icons --print

# If templates exist but don't match, rebuild with current mod files
./build_database.sh
```

### Low Confidence Scores

**Problem:**
Items detected but with low confidence scores.

**This is normal in some cases:**
- Some items naturally have lower match confidence due to similar icons
- Lighting/gamma variations in screenshots
- Mod version mismatch between screenshot and database

**Solution:**
1. Check if items are correctly identified despite low confidence
   - Low confidence doesn't mean incorrect — verify the match is right

2. Verify screenshot quality (resolution, compression)

3. Check template quality:
   ```bash
   fs-tools inspect --database templates.h5 --resolution 1080 --code ItemCode --print
   ```

4. Rebuild database if using different mod versions

### Incorrect Quantities Detected

**Problem:**
Items detected correctly but quantities are wrong.

**Possible Causes:**

1. **OCR model issue**
   - Verify custom Tesseract model is loaded
   - Check logs for OCR warnings

2. **Screenshot quality**
   - Quantity boxes must be clear and unobstructed
   - Avoid screenshots with UI overlays

3. **Calibration needed**
   - OCR detection boxes may need adjustment for your resolution
   - See [Configuration](configuration.md) OCR settings

## API Server Issues

### Port Already in Use

**Problem:**
```
ERROR: [Errno 48] Address already in use
```

**Solution:**
1. Use a different port:
   ```bash
   uvicorn foxhole_stockpiles.api.server:app --port 8001
   ```

2. Or kill the process using port 8000:
   ```bash
   # Find process
   lsof -i :8000
   # Kill it
   kill -9 <PID>
   ```

### API Authentication Failing

**Problem:**
```json
{
  "detail": "Authentication required"
}
```

**Solution:**
1. Verify authentication is configured:
   ```bash
   echo $FS_API_AUTH__AUTH_TYPE
   echo $FS_API_AUTH__AUTH_TOKEN
   ```

2. Check your request includes the correct header:
   ```bash
   # Bearer auth
   curl -H "Authorization: Bearer your-token" http://localhost:8000/ocr/scan_image

   # Custom header
   curl -H "X-API-Key: your-token" http://localhost:8000/ocr/scan_image
   ```

3. Verify token matches:
   ```bash
   # Test without auth (if disabled)
   unset FS_API_AUTH__AUTH_TYPE
   unset FS_API_AUTH__AUTH_TOKEN
   # Restart server and try again
   ```

### API Returns 400 Bad Request

**Problem:**
```json
{
  "detail": "File must be an image"
}
```

**Solution:**
1. Verify you're sending a file, not a path:
   ```bash
   # Correct: -F sends file content
   curl -F "image=@screenshot.png" http://localhost:8000/ocr/scan_image

   # Wrong: this sends the string "screenshot.png"
   curl -d "image=screenshot.png" http://localhost:8000/ocr/scan_image
   ```

2. Check content type:
   ```bash
   file screenshot.png  # Should show "PNG image data"
   ```

## Webhook Issues

### Webhook Not Receiving Data

**Problem:**
Scanner completes but webhook doesn't receive the payload.

**Solution:**
1. Check webhook configuration:
   ```bash
   echo $FS_OUTPUT__FORMAT  # Should be "webhook"
   echo $FS_OUTPUT__WEBHOOK_URL    # Should be valid URL
   ```

2. Verify webhook URL is accessible:
   ```bash
   curl -X POST $FS_OUTPUT__WEBHOOK_URL \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

3. Check logs for webhook errors:
   ```bash
   export FS_LOGGING__LOG_LEVEL=DEBUG
   # Check output for webhook connector errors
   ```

### Webhook Returns 401 Unauthorized

**Problem:**
Webhook receives request but rejects it.

**Solution:**
1. Verify webhook authentication is configured:
   ```bash
   echo $FS_OUTPUT__WEBHOOK_AUTH_TYPE
   echo $FS_OUTPUT__WEBHOOK_TOKEN
   ```

2. Check authentication matches webhook expectations:
   ```bash
   # Test webhook manually
   curl -X POST https://your-webhook.com \
     -H "Authorization: Bearer $FS_OUTPUT__WEBHOOK_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

### Connection Timeout

**Problem:**
```
ConnectTimeout occurred. Retrying (1/3)...
```

**Solution:**
1. Verify webhook server is running
2. Check network connectivity:
   ```bash
   ping your-webhook-domain.com
   curl -I https://your-webhook-domain.com
   ```
3. Check firewall rules
4. Verify URL is correct (https:// vs http://)

## Template Generation Issues

### Missing Game Assets

**Problem:**
```
FileNotFoundError: Asset not found: path/to/icon.png
```

**Solution:**
1. Verify assets were extracted:
   ```bash
   ls raw_assets/  # Should contain PNG files
   ```

2. Re-run asset extraction:
   ```bash
   fs-tools extract-assets \
     --catalog catalog.json \
     --pak /path/to/game.pak \
     --output raw_assets/
   ```

### Template Generation Fails

**Problem:**
Template generation completes but produces no templates.

**Solution:**
1. Check catalog.json is valid:
   ```bash
   python -m json.tool catalog.json > /dev/null
   ```

2. Verify asset paths in catalog match extracted files

3. Check for errors in logs:
   ```bash
   export FS_LOGGING__LOG_LEVEL=DEBUG
   fs-tools generate-templates --catalog catalog.json --assets raw_assets/ --templates output/
   ```

## Configuration Issues

### Environment Variables Not Working

**Problem:**
Settings don't change when setting environment variables.

**Solution:**
1. Verify variable names use correct format:
   ```bash
   # Correct
   export FS_API_AUTH__AUTH_TYPE=bearer

   # Wrong (underscore instead of double underscore)
   export FS_API_AUTH_AUTH_TYPE=bearer
   ```

2. Check variable is exported:
   ```bash
   echo $FS_API_AUTH__AUTH_TYPE
   ```

3. Restart the application after setting variables

### Config File Ignored

**Problem:**
Settings in `~/.fs_config` are not being used.

**Solution:**
1. Verify file location:
   ```bash
   ls -la ~/.fs_config
   ```

2. Check JSON syntax is valid:
   ```bash
   python -m json.tool ~/.fs_config
   ```

3. Remember: Environment variables override config file

## Getting Help

If you're still experiencing issues:

1. **Enable debug logging:**
   ```bash
   export FS_LOGGING__LOG_LEVEL=DEBUG
   export FS_LOGGING__LOG_FILE=/tmp/foxhole-scanner.log
   ```

2. **Collect information:**
   - Python version: `python --version`
   - Tesseract version: `tesseract --version`
   - Operating system
   - Screenshot resolution
   - Full error message and stack trace

3. **Check existing issues:**
   - Search [GitHub Issues](https://github.com/xurxogr/foxhole-stockpiles/issues)

4. **Create a new issue:**
   - Include all collected information
   - Provide a minimal reproduction example
   - Attach logs (redact sensitive information)

## See Also

- [Configuration Guide](configuration.md) - All configuration options
- [API Usage](api-usage.md) - API server documentation
- [Webhooks](webhooks.md) - Webhook integration guide
