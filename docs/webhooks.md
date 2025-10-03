# Webhook Integration

The Foxhole Stockpile Scanner can send scan results to webhooks, enabling integration with external systems, Discord bots, databases, and more.

## Overview

When configured with webhook output, the scanner sends a POST request with the stockpile data to your specified URL.

## Configuration

### Basic Webhook Setup

Set the output format to webhook and provide a URL:

```bash
export FS_OUTPUT_FORMAT__OUTPUT_FORMAT=webhook
export FS_OUTPUT_FORMAT__WEBHOOK_URL=https://api.example.com/stockpiles
```

Or in `~/.fs_config`:
```json
{
  "output_format": {
    "output_format": "webhook",
    "webhook_url": "https://api.example.com/stockpiles"
  }
}
```

### Webhook Authentication

Webhooks support three authentication methods:

#### 1. Bearer Token

```bash
export FS_OUTPUT_FORMAT__WEBHOOK_AUTH_TYPE=bearer
export FS_OUTPUT_FORMAT__WEBHOOK_TOKEN=your-webhook-token
```

Sends: `Authorization: Bearer your-webhook-token`

#### 2. Basic Authentication

```bash
export FS_OUTPUT_FORMAT__WEBHOOK_AUTH_TYPE=basic
export FS_OUTPUT_FORMAT__WEBHOOK_TOKEN=$(echo -n "user:pass" | base64)
```

Sends: `Authorization: Basic dXNlcjpwYXNz`

#### 3. Custom Header

```bash
export FS_OUTPUT_FORMAT__WEBHOOK_AUTH_TYPE=X-API-Key
export FS_OUTPUT_FORMAT__WEBHOOK_TOKEN=custom-api-key-123
```

Sends: `X-API-Key: custom-api-key-123`

## API to Webhook Passthrough

When using the API server, you can pass client authentication through to the webhook:

```bash
# Configure which header to forward
export FS_OUTPUT_FORMAT__WEBHOOK_CLIENT_AUTH_HEADER=Authorization
```

Client request:
```bash
curl -X POST http://localhost:8000/ocr/scan_image \
  -H "Authorization: Bearer client-token" \
  -F "image=@screenshot.png"
```

The API will forward this token to the webhook, **overriding** the configured `webhook_token`.

### Use Case: Multi-Tenant API

```bash
# API uses one auth for clients
export FS_API_AUTH__AUTH_TYPE=bearer
export FS_API_AUTH__AUTH_TOKEN=api-server-token

# Each client's token is forwarded to webhook
export FS_OUTPUT_FORMAT__WEBHOOK_CLIENT_AUTH_HEADER=X-Client-ID
export FS_OUTPUT_FORMAT__WEBHOOK_URL=https://api.example.com/stockpiles
```

Clients send their own token:
```bash
curl -X POST http://localhost:8000/ocr/scan_image \
  -H "Authorization: Bearer api-server-token" \
  -H "X-Client-ID: client-abc-123" \
  -F "image=@screenshot.png"
```

The webhook receives `X-Client-ID: client-abc-123`.

## Webhook Payload

### Request Format

**Method:** POST
**Content-Type:** application/json

**Body:**
```json
{
  "name": "Logi",
  "type": "seaport",
  "hex_name": "Terminus",
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

### Expected Response

Your webhook should return a JSON response:

**Success (200):**
```json
{
  "message": "Stockpile received successfully",
  "stockpile_id": "abc123"
}
```

**Error (4xx/5xx):**
```json
{
  "error": "Invalid stockpile data"
}
```

The scanner will log the response but doesn't retry on failure.

## Retry Behavior

The webhook connector includes automatic retry for connection timeouts:
- **Max retries:** 3
- **Delay between retries:** 2 seconds
- **Only retries on:** Connection timeout errors
- **Does not retry on:** HTTP errors (4xx, 5xx)

## Testing Webhooks

### Local Testing with RequestBin

1. Create a temporary webhook URL at [RequestBin](https://requestbin.com/)
2. Configure the scanner:
   ```bash
   export FS_OUTPUT_FORMAT__WEBHOOK_URL=https://requestbin.com/r/your-bin-id
   ```
3. Run a scan and check RequestBin to see the payload

### Local Testing with netcat

```bash
# Listen on port 5000
nc -l 5000

# Configure scanner
export FS_OUTPUT_FORMAT__WEBHOOK_URL=http://localhost:5000
```

### Testing with webhook.site

1. Go to [webhook.site](https://webhook.site/)
2. Copy your unique URL
3. Configure:
   ```bash
   export FS_OUTPUT_FORMAT__WEBHOOK_URL=https://webhook.site/your-unique-id
   ```

## Error Handling

The webhook connector handles these error scenarios:

| Error | Behavior |
|-------|----------|
| Connection timeout | Retry up to 3 times with 2s delay |
| HTTP 4xx/5xx | Log error, no retry |
| Invalid JSON response | Log warning, continue |
| Empty payload | Skip webhook, return error message |
| Missing webhook URL | Skip webhook, return error message |

Error responses are logged and returned in the API response when using the API server.

## Security Considerations

1. **Use HTTPS:** Always use HTTPS URLs for webhooks in production
2. **Authenticate requests:** Configure `webhook_auth_type` and `webhook_token`
3. **Validate incoming data:** Verify authentication on your webhook endpoint
4. **Rate limiting:** Implement rate limiting on your webhook server
5. **Timeout handling:** Set reasonable timeouts on your webhook endpoint

## Debugging

Enable debug logging to see webhook request/response details:

```bash
export FS_LOGGING__LOG_LEVEL=DEBUG
export FS_LOGGING__LOGGERS='{"foxhole_stockpiles.connectors.webhook": "DEBUG"}'
```

This will log:
- Webhook URL being called
- Authentication headers (redacted)
- Response status and body
- Retry attempts

## Common Issues

### Webhook returns 401 Unauthorized

Check that your `webhook_token` matches what the endpoint expects:
```bash
# Verify token is set correctly
echo $FS_OUTPUT_FORMAT__WEBHOOK_TOKEN

# Test webhook manually
curl -X POST https://your-webhook.com \
  -H "Authorization: Bearer $FS_OUTPUT_FORMAT__WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Connection timeout errors

- Verify the webhook URL is accessible
- Check firewall/network settings
- Ensure the webhook server is running
- Try increasing timeout (requires code modification)

### Webhook receives empty data

Check that the scanner successfully detected items:
```bash
# Test scanner with console output first
export FS_OUTPUT_FORMAT__OUTPUT_FORMAT=console
fs scanner --image screenshot.png
```

## See Also

- [API Usage](api-usage.md) - Using the API server with webhooks
- [API Authentication](api-authentication.md) - Authenticating API requests
- [Configuration](configuration.md) - All configuration options
