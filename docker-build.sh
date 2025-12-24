#!/bin/bash
# Docker build script with git information
# Usage: ./docker-build.sh [OPTIONS]
# Example: ./docker-build.sh --build-arg PYTHON_VERSION=3.13

set -e

# Capture git information
if [ -d .git ]; then
    GIT_COMMIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    GIT_COMMIT_SHORT_HASH=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "unknown")
    GIT_COMMIT_DATE=$(git log -1 --format=%cd --date=short 2>/dev/null || echo "unknown")

    # Check if working directory is dirty
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        GIT_DIRTY="dirty"
    else
        GIT_DIRTY="clean"
    fi
else
    echo "Warning: Not a git repository. Building without git info."
    GIT_COMMIT_HASH="unknown"
    GIT_COMMIT_SHORT_HASH="unknown"
    GIT_COMMIT_DATE="unknown"
    GIT_DIRTY="unknown"
fi

echo "Building Docker image with git info:"
echo "  Commit: ${GIT_COMMIT_SHORT_HASH}"
echo "  Date:   ${GIT_COMMIT_DATE}"
echo "  Status: ${GIT_DIRTY}"
echo ""

# Build Docker image with git information
docker build \
    --build-arg GIT_COMMIT_HASH="${GIT_COMMIT_HASH}" \
    --build-arg GIT_COMMIT_SHORT_HASH="${GIT_COMMIT_SHORT_HASH}" \
    --build-arg GIT_COMMIT_DATE="${GIT_COMMIT_DATE}" \
    --build-arg GIT_DIRTY="${GIT_DIRTY}" \
    "$@" \
    -t fs:latest \
    .

echo ""
echo "Build complete! Image tagged as: fs:latest"
echo "Git info baked into image:"
echo "  Commit: ${GIT_COMMIT_SHORT_HASH}"
echo "  Date:   ${GIT_COMMIT_DATE}"
echo "  Status: ${GIT_DIRTY}"
