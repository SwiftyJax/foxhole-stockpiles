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
FileNotFoundError: Database file not found: foxhole_templates.pkl
```

**Solution:**
1. Build the database first:
   ```bash
   fs database-builder \
     --catalog catalog.json \
     --templates processed_templates/ \
     --database foxhole_templates.pkl
   ```

2. Or specify the correct path:
   ```bash
   fs scanner --database /path/to/database.pkl --image screenshot.png
   ```

3. Or set via environment variable:
   ```bash
   export FS_SCANNER__DATABASE_PATH=/path/to/database.pkl
   ```

### No Items Detected

**Problem:**
Scanner completes but finds 0 items in the screenshot.

**Possible Causes & Solutions:**

1. **Wrong resolution database**
   - Verify your screenshot resolution matches the database
   - Check database resolutions: `fs inspect --database templates.pkl`
   - Rebuild database with correct resolution

2. **Screenshot quality**
   - Use native game resolution screenshots (1080p, 1440p, 2160p)
   - Avoid compressed or scaled images
   - Use PNG format (lossless compression)

3. **Incorrect screenshot type**
   - Scanner expects stockpile inventory screenshots
   - Screenshot must show the stockpile grid with items
   - Title bar must be visible

4. **Confidence threshold too high**
   - The default confidence threshold (0.85) may be too strict for some images
   - Try lowering it to detect more items:
     ```bash
     export FS_SCANNER__CONFIDENCE_THRESHOLD=0.75
     fs scanner --database templates.pkl --image screenshot.png
     ```
   - Or set resolution-specific thresholds:
     ```bash
     export FS_SCANNER__CONFIDENCE_BY_RESOLUTION__1080=0.75
     export FS_SCANNER__CONFIDENCE_BY_RESOLUTION__2160=0.80
     ```
   - **Note:** Lower thresholds may increase false positives

5. **Debug the detection**
   ```bash
   export FS_SCANNER__DEBUG_OUTPUT_PATH=/tmp/debug/
   export FS_LOGGING__LOG_LEVEL=DEBUG
   fs scanner --database templates.pkl --image screenshot.png
   ```
   Check `/tmp/debug/` for intermediate detection images.

### Some Items Not Detected

**Problem:**
Scanner detects most items but misses some specific ones.

**Solution:**

1. **Check confidence scores in output**
   - Items below the confidence threshold are filtered out
   - Look for warnings in debug logs about low-confidence detections

2. **Lower the confidence threshold**
   ```bash
   # Global threshold
   export FS_SCANNER__CONFIDENCE_THRESHOLD=0.75

   # Or resolution-specific
   export FS_SCANNER__CONFIDENCE_BY_RESOLUTION__1080=0.75
   ```

3. **Verify the item exists in database**
   ```bash
   fs inspect --database templates.pkl --code ItemCode
   ```

4. **Screenshot quality issues**
   - Ensure the screenshot resolution matches a database resolution
   - Avoid screenshots with compression artifacts
   - Make sure items are fully visible (not cut off)

5. **Resolution mismatch**
   - The scanner performs best when screenshot resolution exactly matches a database resolution
   - Supported resolutions: 720p, 1080p, 1440p, 2160p
   - Check what resolutions are in your database:
     ```bash
     fs inspect --database templates.pkl
     ```

**Finding the right threshold:**
1. Start with default (0.85)
2. If items are missing, reduce by 0.05 increments (0.80, 0.75, 0.70)
3. Monitor for false positives
4. Set resolution-specific thresholds if needed (higher resolution can use higher thresholds)

See [Configuration Guide](configuration.md) for details on setting confidence thresholds.

### Low Confidence Scores

**Problem:**
Items detected but with low confidence scores (below 0.85).

**This is normal in some cases:**
- Different screenshot resolutions may require different thresholds
- Some items naturally have lower match confidence
- Lighting/gamma variations in screenshots

**Solution:**
1. Check if items are correctly identified despite low confidence
   - If correct, you can lower the threshold

2. Verify screenshot quality (resolution, compression)

3. Set resolution-specific thresholds:
   ```bash
   export FS_SCANNER__CONFIDENCE_BY_RESOLUTION__1080=0.75
   export FS_SCANNER__CONFIDENCE_BY_RESOLUTION__2160=0.85
   ```

4. Check template quality:
   ```bash
   fs inspect --database templates.pkl --code ItemCode
   ```

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
   echo $FS_OUTPUT_FORMAT__OUTPUT_FORMAT  # Should be "webhook"
   echo $FS_OUTPUT_FORMAT__WEBHOOK_URL    # Should be valid URL
   ```

2. Verify webhook URL is accessible:
   ```bash
   curl -X POST $FS_OUTPUT_FORMAT__WEBHOOK_URL \
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
   echo $FS_OUTPUT_FORMAT__WEBHOOK_AUTH_TYPE
   echo $FS_OUTPUT_FORMAT__WEBHOOK_TOKEN
   ```

2. Check authentication matches webhook expectations:
   ```bash
   # Test webhook manually
   curl -X POST https://your-webhook.com \
     -H "Authorization: Bearer $FS_OUTPUT_FORMAT__WEBHOOK_TOKEN" \
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
   fs extract-assets \
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
   fs generate-templates --catalog catalog.json --assets raw_assets/ --templates output/
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
