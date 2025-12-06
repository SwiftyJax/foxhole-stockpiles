# Docker Deployment Guide

This guide explains how to deploy the Foxhole Stockpile Scanner API server using Docker.

## Quick Start

### Using Docker Compose (Recommended)

1. **Prepare your data directory:**
   ```bash
   mkdir -p data
   # Copy your template database to data/
   cp foxhole_templates.h5 data/
   ```

2. **Start the server:**
   ```bash
   docker-compose up -d
   ```

3. **Check status:**
   ```bash
   docker-compose ps
   docker-compose logs -f api
   ```

4. **Test the API:**
   ```bash
   curl http://localhost:8000/health
   ```

### Using Docker Directly

**Build the image:**
```bash
docker build -t foxhole-stockpiles:latest .
```

**Run the container:**
```bash
docker run -d \
  --name foxhole-api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data:ro \
  -e FS_SCANNER__DATABASE_PATH=/app/data/foxhole_templates.h5 \
  foxhole-stockpiles:latest
```

## Configuration

### Environment Variables

Configure the server using environment variables:

**Server Settings:**
```bash
-e FS_API_SERVER__HOST=0.0.0.0
-e FS_API_SERVER__PORT=8000
-e FS_API_SERVER__WORKERS=4
-e FS_API_SERVER__LOG_LEVEL=info
```

**Authentication:**
```bash
-e FS_API_AUTH__AUTH_TYPE=bearer
-e FS_API_AUTH__AUTH_TOKEN=your-secret-token
```

**CORS:**
```bash
-e FS_API_SERVER__CORS_ALLOW_ORIGINS='["https://yourdomain.com"]'
```

**Scanner:**
```bash
-e FS_SCANNER__DATABASE_PATH=/app/data/foxhole_templates.h5
-e FS_SCANNER__CONFIDENCE_THRESHOLD=0.85
-e FS_SCANNER__EARLY_EXIT_THRESHOLD=0.95
-e FS_SCANNER__MAX_NCC_CANDIDATES=25
-e FS_SCANNER__PHASH_THRESHOLD=12
```

**Note:** Lower confidence thresholds detect more items but may increase false positives. Adjust based on your needs.

See [Configuration Guide](configuration.md) for all available options.

### Volume Mounts

**Required:**
- `-v /path/to/data:/app/data:ro` - Template database directory (read-only)

**Optional:**
- `-v /path/to/tessdata:/app/tessdata:ro` - Custom Tesseract models (read-only)

### Environment Configuration

Create a `.env` file for custom configuration (see `.env.example`):

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env
```

**Example `.env` file:**
```bash
# Database configuration (required)
FS_DATA_DIR=./data
FS_SCANNER__DATABASE_PATH=/app/data/foxhole_templates.h5

# Scanner settings (optional)
FS_CONFIDENCE_THRESHOLD=0.85
FS_EARLY_EXIT_THRESHOLD=0.95

# API authentication (optional, for production)
API_TOKEN=your-secret-token-here
```

The docker-compose.yml will automatically use these values.

## Production Deployment

### Best Practices

1. **Use authentication:**
   ```yaml
   environment:
     - FS_API_AUTH__AUTH_TYPE=bearer
     - FS_API_AUTH__AUTH_TOKEN=${API_TOKEN}
   ```

2. **Restrict CORS:**
   ```yaml
   environment:
     - FS_API_SERVER__CORS_ALLOW_ORIGINS=["https://yourdomain.com"]
   ```

3. **Use secrets management:**
   ```bash
   # Create .env file (don't commit!)
   echo "API_TOKEN=your-secret-token" > .env

   # Reference in docker-compose.yml
   environment:
     - FS_API_AUTH__AUTH_TOKEN=${API_TOKEN}
   ```

4. **Set resource limits:**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         cpus: '1'
         memory: 1G
   ```

5. **Use a reverse proxy:**
   - Nginx or Caddy for HTTPS termination
   - Rate limiting
   - Load balancing

### Example with Nginx

**docker-compose.yml:**
```yaml
services:
  api:
    # ... your api configuration
    expose:
      - "8000"
    networks:
      - internal

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    networks:
      - internal

networks:
  internal:
```

## Troubleshooting

### Container won't start

**Check logs:**
```bash
docker logs foxhole-api
# Or with compose:
docker-compose logs api
```

### Database not found

**Ensure the database file exists:**
```bash
# Check local file exists
ls -lh data/foxhole_templates.h5

# Copy database if needed
cp database/db.h5 data/foxhole_templates.h5
```

**Verify volume mount:**
```bash
docker exec foxhole-api ls -la /app/data
```

**Check environment variable:**
```bash
docker exec foxhole-api env | grep FS_SCANNER__DATABASE_PATH
```

### Port already in use

**Change the host port:**
```bash
docker run -p 8080:8000 ...
# Or in docker-compose.yml:
ports:
  - "8080:8000"
```

### Health check failing

**Test manually:**
```bash
docker exec foxhole-api curl http://localhost:8000/health
```

### Permission denied

The container runs as non-root user (uid 1000). Ensure mounted volumes have correct permissions:
```bash
chown -R 1000:1000 data/
```

## Image Information

**Base image:** python:3.12-slim

**Installed packages:**
- Python 3.12
- FastAPI & Uvicorn
- OpenCV, NumPy, Pydantic
- Tesseract OCR
- All dependencies from pyproject.toml

**Image size:** ~400-500MB

**Security features:**
- Non-root user (appuser, uid 1000)
- Minimal base image (slim)
- No unnecessary packages
- Read-only volume mounts
- No editable package install (production-ready)

## Building Custom Images

### Build with different base

```dockerfile
# Use different Python version
FROM python:3.13-slim AS builder
```

### Add custom dependencies

```dockerfile
# In builder stage, before pip install
RUN apt-get update && apt-get install -y your-package
```

### Build arguments

```bash
docker build \
  --build-arg PYTHON_VERSION=3.13 \
  -t foxhole-stockpiles:3.13 \
  .
```

## Monitoring

### Health Checks

The container includes built-in health checks:

```bash
docker inspect --format='{{.State.Health.Status}}' foxhole-api
```

### Logs

**Follow logs:**
```bash
docker-compose logs -f api
```

**View last 100 lines:**
```bash
docker-compose logs --tail=100 api
```

### Metrics

For production, consider adding:
- Prometheus exporter
- Grafana dashboards
- APM tools (DataDog, New Relic)

## Updates

**Pull latest code and rebuild:**
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

**Rolling updates (zero downtime):**
```bash
docker-compose up -d --scale api=2
docker-compose up -d --scale api=1
```

## Cleanup

**Stop and remove containers:**
```bash
docker-compose down
```

**Remove volumes:**
```bash
docker-compose down -v
```

**Remove images:**
```bash
docker rmi foxhole-stockpiles:latest
```

## See Also

- [API Usage Guide](api-usage.md) - API endpoints and authentication
- [Configuration Guide](configuration.md) - All configuration options
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
