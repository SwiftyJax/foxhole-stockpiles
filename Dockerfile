# Multi-stage build for smaller final image
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy pyproject.toml and create minimal package structure for dependency installation
COPY pyproject.toml /app/
WORKDIR /app
# Create a dummy __init__.py so pip can install dependencies from pyproject.toml
RUN mkdir -p foxhole_stockpiles && touch foxhole_stockpiles/__init__.py

# Install dependencies from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .[server] && \
    # Strip debug symbols and remove .so.dbg files
    find /opt/venv -name "*.so" -exec strip --strip-debug {} \; 2>/dev/null || true


# Final stage - minimal runtime image
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    tesseract-ocr \
    libtesseract-dev \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-rus \
    tesseract-ocr-chi-sim \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY foxhole_stockpiles /app/foxhole_stockpiles

# Set up working directory
WORKDIR /app

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Add /app to PYTHONPATH so imports work
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the server using Python module
# Note: Configure via environment variables or docker-compose.yml
# See docs/docker.md for configuration options
CMD ["python", "-m", "foxhole_stockpiles.commands.api_server.api_server"]
