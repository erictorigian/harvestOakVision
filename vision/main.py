"""
Harvest Oak Vision Engine — Vision Service Entry Point

Loop:
  1. Read frame from camera
  2. Run board detector (MOG2 tripwire)
  3. Run speed calculator (Lucas-Kanade optical flow)
  4. Run downtime state machine
  5. Every 1s: publish metrics to API via WebSocket
  6. Every 1m: write production_metrics rollup to DB
  7. Per crossing event: write piece_event to DB
  8. On downtime end: write downtime_event to DB
  9. If DEBUG_OVERLAY=true: serve annotated MJPEG at :8080
"""
from __future__ import annotations

import asyncio
import base64
import collections
import io
import logging
import os
import time
from datetime import datetime, timezone
from threading import Thread, Lock
from typing import Optional

import cv2
import numpy as np

from vision.hardware import detect_hardware
from vision.camera import CameraSource
from vision.detector import BoardDetector
from vision.speed import SpeedCalculator
from vision.belt_speed import BeltSpeedTracker
from vision.downtime import DowntimeTracker
from vision.publisher import MetricsPublisher
import vision.db as vision_db

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
logger = logging.getLogger("harvest_oak.vision")

DEBUG_OVERLAY = os.environ.get("DEBUG_OVERLAY", "false").lower() == "true"


# ── Debug MJPEG HTTP server ─────────────────────────────────────────────────────

_latest_debug_frame: Optional[bytes] = None
_debug_lock = Lock()


def _mjpeg_server():
    """Simple single-threaded MJPEG server at port 8080."""
    import socket
    import struct

    HOST, PORT = "0.0.0.0", 8080
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(5)
    logger.info(f"Debug MJPEG server listening on :{PORT}")

    def handle(conn):
        # Minimal HTTP response
        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n"
        )
        conn.sendall(header.encode())
        while True:
            with _debug_lock:
                frame_bytes = _latest_debug_frame
            if frame_bytes:
                part = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame_bytes
                    + b"\r\n"
                )
                try:
                    conn.sendall(part)
                except BrokenPipeError:
                    break
            time.sleep(0.1)
        conn.close()

    while True:
        conn, _ = srv.accept()
        t = Thread(target=handle, args=(conn,), daemon=True)
        t.start()


# ── Main async loop ────────────────────────────────────────────────────────────

async def run():
    # Hardware detection
    hw = detect_hardware()
    logger.info(f"Hardware profile: {hw}")

    # Apply OpenCV thread limit for Pi
    cv2_threads = hw.get("cv2_threads", 4)
    cv2.setNumThreads(cv2_threads)

    # Initialize components
    camera = CameraSource(hw)
    detector = BoardDetector()
    speed_calc = SpeedCalculator(hw["frame_width"])
    belt_speed = BeltSpeedTracker()
    downtime_tracker = DowntimeTracker()
    publisher = MetricsPublisher()

    # DB init
    await vision_db.init_pool()

    # Start debug MJPEG server in background thread if requested
    if DEBUG_OVERLAY:
        t = Thread(target=_mjpeg_server, daemon=True)
        t.start()

    # Connect to camera
    while not camera.connect():
        logger.warning("Camera not available, retrying...")
        await asyncio.sleep(2)

    # Connect publisher (non-blocking — will retry)
    await publisher.connect()

    detection_fps = hw["detection_fps"]
    frame_interval = 1.0 / detection_fps

    # Rolling counters
    pieces_this_minute: int = 0
    speeds_this_minute: list[float] = []
    downtime_this_minute: int = 0

    last_publish_time = time.time()
    last_minute_rollup = time.time()
    last_piece_times: collections.deque = collections.deque(maxlen=120)

    shift_id: Optional[int] = None
    shift_refresh_interval = 30.0
    last_shift_refresh = 0.0

    frame_count = 0
    loop_start = time.time()

    while True:
        frame_start = time.time()

        # Refresh active shift ID periodically
        if frame_start - last_shift_refresh > shift_refresh_interval:
            shift_id = await vision_db.get_active_shift_id()
            last_shift_refresh = frame_start

        # Read frame
        frame = camera.read_frame()
        if frame is None:
            downtime_tracker.update(0, 0.0, None, camera_ok=False)
            camera.reconnect_if_needed()
            await asyncio.sleep(0.5)
            continue

        # Detection
        new_pieces, events, debug_frame = detector.process_frame(frame, debug=DEBUG_OVERLAY)

        # Speed (optical flow)
        fpm_instant, fpm_smoothed = speed_calc.process_frame(frame)

        # Outfeed belt speed (silver tape tracking)
        outfeed_instant, outfeed_smoothed = belt_speed.process_frame(frame)

        # Draw detected tape marks on debug overlay
        if DEBUG_OVERLAY and debug_frame is not None:
            for (tx, ty) in belt_speed._prev_centroids:
                cv2.circle(debug_frame, (int(tx), int(ty)), 10, (255, 165, 0), 2)
                cv2.putText(debug_frame, "TAPE", (int(tx) + 12, int(ty) + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 165, 0), 1)
            if belt_speed._pixels_per_inch:
                cv2.putText(debug_frame,
                            f"Belt: {outfeed_instant:.1f} FPM ({belt_speed._pixels_per_inch:.1f}px/in)",
                            (10, debug_frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 165, 0), 2)

        # Motion level (for downtime detection)
        fg_mask = detector.get_fg_mask(frame)
        motion = detector.motion_level(fg_mask)

        # Downtime — take whichever speed source is non-zero.
        # Optical flow (fpm_smoothed) fails on smooth belt surfaces; tape tracker
        # (outfeed_smoothed) is more reliable when tape marks are present.
        effective_speed = max(fpm_smoothed, outfeed_smoothed)
        state = downtime_tracker.update(new_pieces, motion, frame, camera_ok=True, belt_speed_fpm=effective_speed)

        # Accumulate minute stats
        pieces_this_minute += new_pieces
        if fpm_smoothed > 0:
            speeds_this_minute.append(fpm_smoothed)

        # DB: piece events
        for event in events:
            await vision_db.insert_piece_event(
                direction=event["direction"],
                confidence=event["confidence"],
                line_speed_fpm=fpm_smoothed,
                shift_id=shift_id,
            )
            last_piece_times.append(frame_start)

        # DB: completed downtime events
        completed = downtime_tracker.pop_completed_events()
        for rec in completed:
            await vision_db.insert_downtime_event(
                start_ts=datetime.fromtimestamp(rec.start_time, tz=timezone.utc),
                end_ts=datetime.fromtimestamp(rec.end_time, tz=timezone.utc),
                duration_seconds=rec.duration_seconds,
                state=rec.state,
                snapshot_path=rec.snapshot_path,
                shift_id=shift_id,
            )

        # Publish metrics every second
        now = time.time()
        if now - last_publish_time >= 1.0:
            total_today = await vision_db.get_today_piece_count()
            downtime_today = await vision_db.get_today_downtime_seconds()

            # Pieces in last 60 seconds
            cutoff = now - 60
            recent_pieces = sum(1 for t in last_piece_times if t >= cutoff)
            pph_current = recent_pieces * 60

            debug_b64 = None
            if DEBUG_OVERLAY and debug_frame is not None:
                _, jpg = cv2.imencode(".jpg", debug_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                jpg_bytes = jpg.tobytes()
                with _debug_lock:
                    _latest_debug_frame = jpg_bytes
                debug_b64 = base64.b64encode(jpg_bytes).decode()

            metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "state": state,
                "total_pieces_today": total_today,
                "pieces_last_minute": recent_pieces,
                "pieces_per_hour_current": pph_current,
                "line_speed_fpm": round(fpm_instant, 2),
                "line_speed_fpm_smoothed": round(fpm_smoothed, 2),
                "outfeed_belt_speed_fpm": round(outfeed_instant, 2),
                "outfeed_belt_speed_fpm_smoothed": round(outfeed_smoothed, 2),
                "downtime_seconds_today": downtime_today,
                "current_downtime_duration": downtime_tracker.current_downtime_duration,
                "shift_id": shift_id,
                "frame_debug_jpeg_b64": debug_b64,
            }
            await publisher.publish(metrics)
            last_publish_time = now

        # 1-minute DB rollup
        if now - last_minute_rollup >= 60.0:
            avg_speed = float(np.mean(speeds_this_minute)) if speeds_this_minute else 0.0
            await vision_db.upsert_production_metric(
                pieces_count=pieces_this_minute,
                avg_speed_fpm=round(avg_speed, 2),
                downtime_seconds=downtime_tracker.current_downtime_duration,
                state=state,
                shift_id=shift_id,
            )
            pieces_this_minute = 0
            speeds_this_minute = []
            last_minute_rollup = now

        frame_count += 1

        # Throttle to target FPS
        elapsed = time.time() - frame_start
        sleep_time = frame_interval - elapsed
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Vision service stopped")


if __name__ == "__main__":
    main()
