#!/usr/bin/env bash
set -euo pipefail

# Alpha-Q Local Docker Build Script (不推送到Hub)
# Usage: ./build-local.sh [--no-cache] [--backend-only] [--frontend-only]

DOCKER_HUB_USER="fuzhouxing"
BACKEND_IMAGE="${DOCKER_HUB_USER}/alpha-q-backend:latest"
FRONTEND_IMAGE="${DOCKER_HUB_USER}/alpha-q-frontend:latest"

BUILD_BACKEND=true
BUILD_FRONTEND=true
CACHE_FLAG=""

# Parse arguments
for arg in "$@"; do
  case $arg in
    --no-cache)
      CACHE_FLAG="--no-cache"
      shift
      ;;
    --backend-only)
      BUILD_FRONTEND=false
      shift
      ;;
    --frontend-only)
      BUILD_BACKEND=false
      shift
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: $0 [--no-cache] [--backend-only] [--frontend-only]"
      exit 1
      ;;
  esac
done

echo "=== Alpha-Q Local Docker Build ==="
echo "Backend:  ${BUILD_BACKEND}"
echo "Frontend: ${BUILD_FRONTEND}"
echo "Cache:    ${CACHE_FLAG:-enabled}"
echo ""

# Build backend
if [ "$BUILD_BACKEND" = true ]; then
  echo "[1/2] Building backend image..."
  docker build ${CACHE_FLAG} -f backend/Dockerfile -t "${BACKEND_IMAGE}" .
  echo "✓ Backend built: ${BACKEND_IMAGE}"
  echo ""
fi

# Build frontend
if [ "$BUILD_FRONTEND" = true ]; then
  echo "[2/2] Building frontend image..."
  docker build ${CACHE_FLAG} -f frontend/Dockerfile -t "${FRONTEND_IMAGE}" frontend/
  echo "✓ Frontend built: ${FRONTEND_IMAGE}"
  echo ""
fi

echo "=== Build Complete ==="
echo "To test locally: docker-compose up -d"
echo "To push to hub: ./build.sh"
