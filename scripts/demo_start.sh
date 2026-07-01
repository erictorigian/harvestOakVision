#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Harvest Oak Vision — Demo Quick Start
#
# Starts the full stack with synthetic data. No camera required.
# Run this before a demo or for development testing.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

cd "$ROOT"

# ── 1. Create data directories ────────────────────────────────────────────────
mkdir -p data/snapshots data/postgres

# ── 2. Create .env if not present ────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    # Patch for demo mode
    sed -i.bak \
        -e "s|^CAMERA_RTSP_URL=.*|# CAMERA_RTSP_URL=|" \
        -e "s|^# TEST_VIDEO_PATH=.*|TEST_VIDEO_PATH=/data/sample_conveyor.mp4|" \
        -e "s|^DEBUG_OVERLAY=.*|DEBUG_OVERLAY=true|" \
        -e "s|^DB_PASSWORD=.*|DB_PASSWORD=testpassword|" \
        .env
    rm -f .env.bak
    echo "Created .env with demo settings"
fi

# ── 3. Generate test video if needed ─────────────────────────────────────────
if [ ! -f "data/sample_conveyor.mp4" ]; then
    echo "Generating synthetic conveyor video (~30s)..."
    if command -v python3 &>/dev/null; then
        # Check if opencv is available
        if python3 -c "import cv2, numpy" 2>/dev/null; then
            python3 scripts/generate_test_video.py data/sample_conveyor.mp4
        else
            echo "  opencv not installed locally — video will be generated inside container"
            echo "  (vision service will start in UNKNOWN state until video is ready)"
        fi
    fi
fi

# ── 4. Build and start the stack ──────────────────────────────────────────────
echo ""
echo "Starting Harvest Oak Vision demo stack..."
echo ""

docker compose \
    -f docker-compose.yml \
    -f docker-compose.demo.yml \
    up --build -d

# ── 5. Wait for seed service to finish ───────────────────────────────────────
echo "Waiting for demo data to load..."
docker compose \
    -f docker-compose.yml \
    -f docker-compose.demo.yml \
    logs -f seed 2>/dev/null || true

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HARVEST OAK VISION — DEMO READY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Dashboard:     http://localhost:3000"
echo "  API health:    http://localhost:8000/api/health"
echo "  Debug feed:    http://localhost:8080/debug_feed"
echo ""
echo "  To reload demo data: python3 scripts/seed_demo.py"
echo "  To stop:             docker compose down"
echo ""

# Open dashboard in browser if on Mac
if [[ "$OSTYPE" == "darwin"* ]]; then
    sleep 2
    open http://localhost:3000
fi
