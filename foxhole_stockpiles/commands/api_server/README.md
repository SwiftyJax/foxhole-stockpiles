# API Server Command

Start the Foxhole Stockpile Scanner API server.

## Installation

The API server requires additional dependencies. Install with:

```bash
pip install -e .[server]
```

## Usage

```bash
fs server [options]
```

Or using the alias:

```bash
fs api [options]
```

## Options

- `--host TEXT` - Bind socket to this host (default: 127.0.0.1)
- `--port INTEGER` - Bind socket to this port (default: 8000)
- `--workers INTEGER` - Number of worker processes (default: 1)
- `--reload` - Enable auto-reload on code changes (development only)
- `--log-level LEVEL` - Log level: critical, error, warning, info, debug, trace (default: info)

## Examples

### Start server on default port

```bash
fs server
```

Server will be available at http://127.0.0.1:8000

### Start server on custom port

```bash
fs server --port 8080
```

### Start server accessible from network

```bash
fs server --host 0.0.0.0 --port 8000
```

### Development mode with auto-reload

```bash
fs server --reload --log-level debug
```

### Production mode with multiple workers

```bash
fs server --host 0.0.0.0 --port 8000 --workers 4
```

## Configuration

The API server can be configured via environment variables. See [Configuration Guide](../../../docs/configuration.md) for details.

### Authentication

Configure authentication before starting the server:

```bash
export FS_API_AUTH__AUTH_TYPE=bearer
export FS_API_AUTH__AUTH_TOKEN=your-secret-token
fs server
```

### CORS Origins

Configure allowed CORS origins:

```bash
export FS_API_SERVER__CORS_ALLOW_ORIGINS='["https://example.com","https://app.example.com"]'
fs server
```

### Database Path

Specify the template database to use:

```bash
export FS_SCANNER__DATABASE_PATH=/path/to/templates.pkl
fs server
```

## API Documentation

Once the server is running, visit:

- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

See [API Usage Guide](../../../docs/api-usage.md) for detailed API documentation.

## Production Deployment

For production deployments:

1. Use multiple workers for better performance
2. Configure authentication
3. Set specific CORS origins (don't use `["*"]`)
4. Use a reverse proxy (nginx, caddy) for HTTPS
5. Consider using a process manager (systemd, supervisor)

Example systemd service:

```ini
[Unit]
Description=Foxhole Stockpile Scanner API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/foxhole-stockpiles
Environment="FS_API_AUTH__AUTH_TYPE=bearer"
Environment="FS_API_AUTH__AUTH_TOKEN=your-secret-token"
Environment="FS_SCANNER__DATABASE_PATH=/opt/foxhole-stockpiles/templates.pkl"
ExecStart=/usr/local/bin/fs server --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

See [Troubleshooting Guide](../../../docs/troubleshooting.md) for common issues.
