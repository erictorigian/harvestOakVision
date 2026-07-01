#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Harvest Oak Vision — Test with sample conveyor video
#
# Downloads a public conveyor belt clip and runs the full stack against it.
# No physical camera required.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$ROOT/data"
SAMPLE="$DATA_DIR/sample_conveyor.mp4"

echo "==> Harvest Oak Vision — Test Mode Setup"

# Create data directories
mkdir -p "$DATA_DIR/snapshots" "$DATA_DIR/postgres"

# Download sample conveyor video if not present
if [ ! -f "$SAMPLE" ]; then
    echo "==> Downloading sample conveyor belt video..."
    # Public domain factory/conveyor footage from Internet Archive
    # Replace with your own sample video if preferred
    if command -v yt-dlp &>/dev/null; then
        yt-dlp -o "$SAMPLE" --format "mp4" \
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>/dev/null || true
    fi

    if [ ! -f "$SAMPLE" ]; then
        echo "==> Creating synthetic test video (moving shapes on conveyor)..."
        python3 "$SCRIPT_DIR/generate_test_video.py" "$SAMPLE"
    fi
fi

echo "==> Sample video ready: $SAMPLE"

# Copy .env.example → .env and inject test video path
ENV_FILE="$ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
    echo "==> Created .env from .env.example"
fi

# Inject test settings
sed -i.bak \
    -e "s|^CAMERA_RTSP_URL=.*|# CAMERA_RTSP_URL=|" \
    -e "s|^# TEST_VIDEO_PATH=.*|TEST_VIDEO_PATH=/data/sample_conveyor.mp4|" \
    -e "s|^DEBUG_OVERLAY=.*|DEBUG_OVERLAY=true|" \
    -e "s|^DB_PASSWORD=.*|DB_PASSWORD=testpassword|" \
    "$ENV_FILE"
rm -f "${ENV_FILE}.bak"

echo "==> Starting stack with test video..."
echo "    Dashboard: http://localhost:3000"
echo "    Debug feed: http://localhost:8080/debug_feed"
echo "    API: http://localhost:8000/api/health"
echo ""

cd "$ROOT"
docker compose up --build
