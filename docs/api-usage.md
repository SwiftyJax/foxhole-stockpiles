# API Usage Guide

The Foxhole Stockpile Scanner provides a REST API for analyzing stockpile screenshots via HTTP.

## Starting the API Server

### Using fs Command (Recommended)

```bash
# Start server on default port (8000)
fs server

# Start on custom port
fs server --port 8080

# Production deployment with multiple workers
fs server --host 0.0.0.0 --port 8000 --workers 4

# Development mode with auto-reload
fs server --reload --log-level debug
```

See [API Server Command Documentation](../foxhole_stockpiles/commands/api_server/README.md) for all options.

### Alternative Methods

**Using Python Module:**
```bash
python -m foxhole_stockpiles.api.server
```

**Using Uvicorn Directly:**
```bash
uvicorn foxhole_stockpiles.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

## Endpoints

### Health Check

**GET /** or **GET /health**

Returns the API health status and version.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

### Scan Stockpile Image

**POST /ocr/scan_image**

Upload and analyze a stockpile screenshot.

**Authentication:** Optional (see [API Authentication](api-authentication.md))

**Parameters:**
- `image` (file, required): Stockpile screenshot (PNG, JPG, JPEG)
- `faction` (query, optional): Filter by faction (`colonials` or `wardens`)
- `language` (query, optional): Language for text detection (`en`, `pt`, `fr`, `de`, `ru`, `zh`)

**Request Example:**
```bash
# Basic request
curl -X POST http://localhost:8000/ocr/scan_image \
  -F "image=@screenshot.png"

# With faction filter
curl -X POST http://localhost:8000/ocr/scan_image \
  -F "image=@screenshot.png" \
  -G -d "faction=colonials"

# With language filter (French stockpile)
curl -X POST http://localhost:8000/ocr/scan_image \
  -F "image=@screenshot.png" \
  -G -d "language=fr"

# With both filters
curl -X POST http://localhost:8000/ocr/scan_image \
  -F "image=@screenshot.png" \
  -G -d "faction=wardens&language=en"

# With authentication
curl -X POST http://localhost:8000/ocr/scan_image \
  -H "Authorization: Bearer your-token" \
  -F "image=@screenshot.png"
```

**Success Response (200):**
```json
{
  "name": "Logi",
  "type": "seaport",
  "shard": "ABLE",
  "ingame_timestamp": "Day 1,293, 1906 Hours",
  "timestamp": "2024-01-04T09:00:00Z",
  "resolution": "1920x1080",
  "errors": [],
  "items": [
    {
      "code": "GrenadeLauncherC",
      "quantity": 3,
      "crated": false,
      "confidence": 0.95
    },
    {
      "code": "RifleW",
      "quantity": 120,
      "crated": true,
      "confidence": 0.92
    }
  ]
}
```

**Error Response (400 - Bad Request):**
```json
{
  "detail": "File must be an image"
}
```

**Error Response (401 - Unauthorized):**
```json
{
  "detail": "Authentication required"
}
```

**Error Response (500 - Server Error):**
```json
{
  "detail": "Unexpected error: Database not found"
}
```

## Response Format

### Stockpile Object

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Stockpile name from in-game screenshot |
| `type` | string | Stockpile type (e.g., `seaport`, `town_base`, `bunker_base`, `storage_depot`) |
| `shard` | string | Game shard (e.g., `ABLE`, `BAKER`, `CHARLIE`) |
| `ingame_timestamp` | string | In-game timestamp from screenshot (e.g., "Day 1,293, 1906 Hours") |
| `timestamp` | string | ISO 8601 timestamp when scan was processed |
| `resolution` | string\|null | Screenshot resolution (e.g., "1920x1080") |
| `errors` | array[string] | List of errors encountered during processing |
| `items` | array | List of detected items (see Item object below) |

### Item Object

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Item code/identifier from the game |
| `quantity` | integer | Item quantity detected (-1 if OCR failed) |
| `crated` | boolean | Whether item is in a crate |
| `confidence` | float\|null | Detection confidence score (0.0-1.0), null if not available |

## Configuration

The API server uses the application configuration. See [Configuration Guide](configuration.md) for details.

### Common Settings

**Database Path:**
```bash
export FS_SCANNER__DATABASE_PATH=/path/to/templates.h5
```

**API Authentication:**
```bash
export FS_API_AUTH__AUTH_TYPE=bearer
export FS_API_AUTH__AUTH_TOKEN=your-secret-token
```

**Output Format (for webhook forwarding):**
```bash
export FS_OUTPUT__FORMAT=webhook
export FS_OUTPUT__WEBHOOK_URL=https://api.example.com/stockpiles
```

**Memory Management:**
```bash
# Enable memory monitoring and statistics (disabled by default)
export FS_API_SERVER__ENABLE_MEMORY_MONITORING=true

# Automatically trim memory after scan requests (enabled by default)
export FS_API_SERVER__AUTO_TRIM_MEMORY=true
```

- `enable_memory_monitoring`: Tracks memory usage per request and exposes `/memory/*` endpoints. Adds slight overhead. Leave disabled unless debugging.
- `auto_trim_memory`: Calls `malloc_trim()` after scans to release memory back to the OS. Prevents memory fragmentation.

## Client Examples

### Python

```python
import requests

url = "http://localhost:8000/ocr/scan_image"
headers = {"Authorization": "Bearer your-token"}

# Optional query parameters
params = {
    "faction": "colonials",  # Optional: colonials or wardens
    "language": "en"         # Optional: en, pt, fr, de, ru, zh
}

with open("screenshot.png", "rb") as f:
    files = {"image": f}
    response = requests.post(url, headers=headers, files=files, params=params)

if response.status_code == 200:
    data = response.json()
    print(f"Found {len(data['items'])} items in {data['name']}")
    for item in data['items']:
        print(f"  - {item['name']}: {item['quantity']}")
else:
    print(f"Error: {response.json()['detail']}")
```

### JavaScript (Node.js)

```javascript
const FormData = require('form-data');
const fs = require('fs');
const fetch = require('node-fetch');

const form = new FormData();
form.append('image', fs.createReadStream('screenshot.png'));

// Build URL with optional query parameters
const params = new URLSearchParams({
  faction: 'colonials',  // Optional: colonials or wardens
  language: 'en'         // Optional: en, pt, fr, de, ru, zh
});

fetch(`http://localhost:8000/ocr/scan_image?${params}`, {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your-token'
  },
  body: form
})
  .then(res => res.json())
  .then(data => {
    console.log(`Found ${data.items.length} items in ${data.name}`);
    data.items.forEach(item => {
      console.log(`  - ${item.name}: ${item.quantity}`);
    });
  })
  .catch(err => console.error('Error:', err));
```

### cURL with jq (for pretty output)

```bash
curl -X POST http://localhost:8000/ocr/scan_image \
  -H "Authorization: Bearer your-token" \
  -F "image=@screenshot.png" \
  | jq '.items[] | "\(.name): \(.quantity)"'
```

## Error Handling

The API returns standard HTTP status codes:

| Code | Description |
|------|-------------|
| 200 | Success - stockpile analyzed |
| 400 | Bad Request - invalid image or parameters |
| 401 | Unauthorized - authentication required or invalid |
| 404 | Not Found - endpoint doesn't exist |
| 405 | Method Not Allowed - wrong HTTP method |
| 413 | Content Too Large - file exceeds 10MB limit |
| 429 | Too Many Requests - rate limit exceeded |
| 500 | Server Error - processing failed |

Always check the `detail` field in error responses for specific error messages.

## CORS Configuration

The API has CORS disabled by default (empty origin list `[]`). For cross-origin requests, configure allowed origins:

**Environment variable:**
```bash
export FS_API_SERVER__CORS_ALLOW_ORIGINS='["https://yourdomain.com","https://app.yourdomain.com"]'
```

**Config file (`~/.fs_config`):**
```json
{
  "api_server": {
    "cors_allow_origins": ["https://yourdomain.com", "https://app.yourdomain.com"]
  }
}
```

**Note:** Same-origin requests (requests from the same host/port as the API) are not affected by CORS configuration.

See [Configuration Guide](configuration.md) for more details.

## Rate Limiting

The API includes built-in rate limiting to prevent abuse:

| Endpoint | Rate Limit |
|----------|------------|
| `/ocr/scan_image` | 30 requests per minute |

When rate limit is exceeded, the API returns HTTP 429 (Too Many Requests):
```json
{
  "detail": "Rate limit exceeded"
}
```

For higher throughput requirements, consider:
- Running multiple API server instances behind a load balancer
- Using a reverse proxy (nginx, Caddy) with custom rate limiting rules

## Authentication

See [API Authentication](api-authentication.md) for detailed authentication setup and examples.

## Webhook Integration

The API can forward results to webhooks. See [Webhooks](webhooks.md) for configuration details.
