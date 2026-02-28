#!/bin/bash
# AgenC OS Build Script
# Builds the Yocto image inside Docker on macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="agenc-yocto-builder"
CONTAINER_NAME="agenc-build"
BUILD_CACHE="$HOME/.agenc-yocto-cache"

echo "=== AgenC OS Build ==="
echo "Project: $PROJECT_DIR"
echo "Cache:   $BUILD_CACHE"

# Create build cache directory
mkdir -p "$BUILD_CACHE"/{downloads,sstate-cache}

# Build Docker image
echo ">>> Building Docker image..."
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

# Run the build
echo ">>> Starting Yocto build (this takes a while on first run)..."
docker run --rm \
    --name "$CONTAINER_NAME" \
    -v "$PROJECT_DIR/meta-agenc:/home/yocto/meta-agenc:ro" \
    -v "$BUILD_CACHE/downloads:/home/yocto/build/downloads" \
    -v "$BUILD_CACHE/sstate-cache:/home/yocto/build/sstate-cache" \
    -v "$BUILD_CACHE/tmp:/home/yocto/build/tmp" \
    "$IMAGE_NAME" \
    "$@"

echo ">>> Build complete."
echo "Image: $BUILD_CACHE/tmp/deploy/images/agenc-one/"
