# Harvest Oak Vision Engine

Real-time piece counting, line speed, and shift analytics for hardwood flooring production.

Single overhead IP camera → board count, FPM speed, downtime detection, shift dashboard.

---

## Prerequisites

**Mac (iMac / Apple Silicon):**
- Docker Desktop — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- Docker Compose v2 (included with Docker Desktop)

**Raspberry Pi 4 (4GB+):**
```bash
curl -fsSL https://get.docker.com | sh
sudo apt install -y docker-compose-plugin
sudo usermod -aG docker $USER
# Log out and back in
```

---

## Quick Start

```bash
# 1. Clone and enter directory
git clone <repo> harvest-oak-vision && cd harvest-oak-vision

# 2. Copy env file and configure
cp .env.example .env

# 3. Set your camera URL (see Camera Setup below)
nano .env   # set CAMERA_RTSP_URL and DB_PASSWORD

# 4. Set your host machine's LAN IP (so dashboard can reach API from browser)
# HOST_IP=192.168.1.xxx in .env

# 5. Start
docker compose up --build

# Dashboard:  http://localhost:3000
# API:        http://localhost:8000/api/health
# Debug feed: http://localhost:8080/debug_feed (when DEBUG_OVERLAY=true)
```

---

## Camera Setup

### Hikvision IP Camera (RTSP)

```
rtsp://admin:YOUR_PASSWORD@CAMERA_IP:554/Streaming/Channels/101
```

- Stream 101 = main stream (high resolution)
- Stream 102 = substream (lower resolution, less CPU)
- Default port: 554
- Default credentials: admin/admin (change in camera web UI)

Set in `.env`:
```bash
CAMERA_RTSP_URL=rtsp://admin:PASSWORD@192.168.1.100:554/Streaming/Channels/102
```

### Dahua / Generic RTSP

```
rtsp://admin:PASSWORD@IP:554/cam/realmonitor?channel=1&subtype=0
```

### USB Camera (testing / no IP camera)

```bash
# In .env:
# CAMERA_RTSP_URL=     ← leave blank
CAMERA_INDEX=0         # 0 = first USB camera
```

### Verify Camera Alignment

1. Set `DEBUG_OVERLAY=true` in `.env`
2. `docker compose up`
3. Open `http://localhost:8080/debug_feed` in browser
4. You'll see the yellow detection line and green bounding boxes
5. Adjust `DETECTION_LINE_Y_PERCENT` until the line crosses where boards pass

---

## Calibration Procedure

Speed accuracy depends on knowing how many feet of conveyor are visible in the frame.

**How to measure:**
1. Place a tape measure along the conveyor in the camera's field of view
2. Note the total feet visible end-to-end
3. Set in `.env`: `CONVEYOR_VISIBLE_FEET=8.5` (example)

Or use the Settings page at `http://localhost:3000/settings` to set and save via the UI.

**Verify speed:** Compare the displayed FPM to a manual measurement (mark a board, time it across the visible span).

---

## Detection Tuning

All parameters are adjustable without code changes. Set in `.env` or the Settings page.

| Parameter | Default | Effect |
|-----------|---------|--------|
| `DETECTION_LINE_Y_PERCENT` | 50 | Move counting tripwire up/down |
| `MIN_CONTOUR_AREA` | 2000 | Increase to reject dust/small debris |
| `COUNT_COOLDOWN_MS` | 800 | Increase if boards are double-counted |
| `DOWNTIME_THRESHOLD_SECONDS` | 45 | Seconds before declaring downtime |
| `DEBUG_OVERLAY` | false | Set true to see what the AI is seeing |

**Common issues:**

- **Double counting:** Increase `COUNT_COOLDOWN_MS` to 1200–1500ms
- **Missing boards:** Decrease `MIN_CONTOUR_AREA` or check lighting
- **Counting shadows:** Increase `MIN_CONTOUR_AREA`; improve lighting uniformity
- **Speed always 0:** Verify `CONVEYOR_VISIBLE_FEET` is set; check debug feed shows belt motion

---

## Raspberry Pi Startup

```bash
# Standard start
docker compose up -d

# Pi-specific (memory limits + ARM64 + Coral passthrough)
docker compose -f docker-compose.yml -f docker-compose.pi.yml up -d
```

**Pi performance notes:**
- Without Coral: runs at 5 FPS detection, 640px frame width — sufficient for most conveyors
- With Coral: 10 FPS detection with TPU-accelerated inference

---

## Google Coral USB TPU Setup (Raspberry Pi)

The Coral USB Accelerator is automatically detected if attached. No config needed.

**udev rules** (run once on Pi):
```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="1a6e", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="18d1", GROUP="plugdev"' | \
    sudo tee /etc/udev/rules.d/65-coral-accelerator.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

**Docker passthrough** is configured in `docker-compose.pi.yml` via:
```yaml
devices:
  - /dev/bus/usb:/dev/bus/usb
```

---

## Test Without a Camera

Generates a synthetic conveyor video and runs the full stack:

```bash
# Requires Python + OpenCV on the host (for video generation)
pip install opencv-python-headless numpy
./scripts/test_with_sample.sh
```

Or generate the test video manually:
```bash
python3 scripts/generate_test_video.py ./data/sample_conveyor.mp4
# Then in .env: TEST_VIDEO_PATH=/data/sample_conveyor.mp4
```

---

## Dashboard Walkthrough

**Live Monitor (`/`)**
- Hero row: total pieces today, pieces/hour current, line speed (FPM), downtime today
- State banner: RUNNING (green) / SLOW (amber) / IDLE (red) / UNKNOWN (gray)
- Piece counter: large animated display, flashes on each new piece
- Downtime table: all stop events today with duration and state

**Shift Analytics (`/shift`)**
- Hourly production bar chart: green = at target, amber = 80–99%, red = below 80%
- Shift timeline: visual representation of running vs downtime periods
- Line speed trend: hourly average FPM
- Shift summary card: total pieces, OEE availability, peak hour, variance vs target

**Settings (`/settings`)**
- Camera URL and test preview
- All detection tuning parameters with sliders
- Speed calibration
- Shift schedule configuration

---

## Shift Management

Shifts can be managed manually via the API or will auto-detect based on the schedule in `.env`.

```bash
# Start a new shift
curl -X POST http://localhost:8000/api/shifts/start \
  -H "Content-Type: application/json" \
  -d '{"label": "Day Shift — May 26"}'

# End current shift (computes all final metrics)
curl -X POST http://localhost:8000/api/shifts/end
```

---

## Troubleshooting

**Camera won't connect:**
```bash
# Test RTSP from host (requires ffmpeg)
ffplay rtsp://admin:PASSWORD@CAMERA_IP:554/Streaming/Channels/101
# If this works, the URL is correct
```

**API unreachable from browser:**
- Set `HOST_IP` in `.env` to your Mac/Pi's LAN IP address (not localhost)
- Rebuild dashboard: `docker compose build dashboard && docker compose up dashboard`

**Database won't start:**
```bash
# Check if port 5432 is already in use
lsof -i :5432
# Stop existing Postgres instance or change port in docker-compose.yml
```

**Boards not being counted:**
1. Open debug feed: `http://localhost:8080/debug_feed`
2. Verify detection line crosses the board path
3. Verify green boxes appear on boards as they pass
4. If no boxes: decrease `MIN_CONTOUR_AREA`; improve lighting
5. If too many boxes: increase `MIN_CONTOUR_AREA`

**Speed reads 0 constantly:**
- Verify `CONVEYOR_VISIBLE_FEET` is set to actual measured value
- The speed calc needs at least 5 trackable features — good results require visible belt texture

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service health + camera status |
| `/api/metrics/live` | GET | Current production state |
| `/api/metrics/today` | GET | Full today summary |
| `/api/metrics/hourly?date=YYYY-MM-DD` | GET | Hourly breakdown |
| `/api/metrics/pieces?start=&end=` | GET | Raw piece events |
| `/api/downtime?date=YYYY-MM-DD` | GET | Downtime events for date |
| `/api/shifts` | GET | All recorded shifts |
| `/api/shifts/start` | POST | Start a new shift |
| `/api/shifts/end` | POST | End current shift |
| `/api/calibrate` | POST | Set conveyor visible feet |
| `/api/settings` | GET/POST | Read/write all settings |
| `/ws/live` | WS | Live metrics stream (1s updates) |

---

*Harvest Oak Vision Engine v1.0 — Phase 1: Piece counting, line speed, shift analytics*
