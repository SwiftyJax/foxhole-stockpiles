# Multi-stage build for smaller final image
# Build with: docker build --build-arg PYTHON_VERSION=3.13 .
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS builder

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
    pip install --no-cache-dir . && \
    # Strip debug symbols and remove .so.dbg files
    find /opt/venv -name "*.so" -exec strip --strip-debug {} \; 2>/dev/null || true


# Final stage - minimal runtime image
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# Build-time git information (passed during docker build)
ARG GIT_COMMIT_HASH=unknown
ARG GIT_COMMIT_SHORT_HASH=unknown
ARG GIT_COMMIT_DATE=unknown
ARG GIT_DIRTY=unknown

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
    libjemalloc2 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY foxhole_stockpiles /app/foxhole_stockpiles

# Set up working directory
WORKDIR /app

# Write git info to file for runtime access
RUN echo "GIT_COMMIT_HASH=${GIT_COMMIT_HASH}" > /app/.git_info && \
    echo "GIT_COMMIT_SHORT_HASH=${GIT_COMMIT_SHORT_HASH}" >> /app/.git_info && \
    echo "GIT_COMMIT_DATE=${GIT_COMMIT_DATE}" >> /app/.git_info && \
    echo "GIT_DIRTY=${GIT_DIRTY}" >> /app/.git_info

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Add /app to PYTHONPATH so imports work
ENV PYTHONPATH=/app

# Use jemalloc for better memory management
# Set to empty string to disable: ENV LD_PRELOAD=
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

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
CMD ["fs", "server"]
