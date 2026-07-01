#!/usr/bin/env python3
"""
Generate a synthetic conveyor belt test video.

Produces a 60-second MP4 with moving rectangular shapes (simulating boards)
traveling left-to-right at a realistic pace. No real camera required for
initial testing and development.
"""
import sys
import math
import random

import cv2
import numpy as np


def generate(output_path: str, duration_sec: int = 60, fps: int = 30):
    width, height = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_sec * fps
    belt_speed_px_per_frame = 8  # ~14 FPM at 1280px = 8ft visible

    # Boards: list of [x, y, w, h, color]
    boards = []
    board_spacing = 180   # pixels between board leading edges
    next_board_x = -200   # start off-screen left

    rng = random.Random(42)

    # Downtime simulation: frames 900-1200 (10s–13.3s) and 2700-2800
    downtime_ranges = [(900, 1200), (2700, 2800)]

    def in_downtime(frame_idx):
        for start, end in downtime_ranges:
            if start <= frame_idx < end:
                return True
        return False

    for frame_idx in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Belt background — dark gray with subtle texture
        frame[:] = (30, 30, 30)
        # Belt texture lines
        for y in range(0, height, 40):
            cv2.line(frame, (0, y), (width, y), (35, 35, 35), 1)

        if not in_downtime(frame_idx):
            # Move existing boards
            for b in boards:
                b[0] += belt_speed_px_per_frame

            # Spawn new board if needed
            if not boards or boards[-1][0] > -board_spacing + belt_speed_px_per_frame * 10:
                # Vary board dimensions slightly for realism
                bw = rng.randint(200, 350)
                bh = rng.randint(60, 100)
                by = (height - bh) // 2 + rng.randint(-20, 20)
                color_val = rng.randint(120, 180)
                boards.append([-bw, by, bw, bh, (40, color_val - 20, color_val)])

            # Remove boards that have exited frame
            boards = [b for b in boards if b[0] < width + 100]

        # Draw boards
        for b in boards:
            x, y, bw, bh, color = b
            if -bw < x < width:
                cv2.rectangle(frame, (max(0, x), y), (min(width, x + bw), y + bh), color, -1)
                # Wood grain lines
                for i in range(0, bw, 15):
                    lx = x + i
                    if 0 <= lx < width:
                        cv2.line(frame, (lx, y), (lx, y + bh),
                                 (color[0] - 15, color[1] - 15, color[2] - 15), 1)

        # Detection line
        line_y = height // 2
        cv2.line(frame, (0, line_y), (width, line_y), (0, 200, 200), 2)

        # Frame counter overlay
        cv2.putText(frame, f"Frame {frame_idx}/{total_frames}  FPS:{fps}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        if in_downtime(frame_idx):
            cv2.putText(frame, "SIMULATED DOWNTIME", (width // 2 - 150, height // 2 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 2)

        writer.write(frame)

        if frame_idx % (fps * 5) == 0:
            print(f"  Generating: {frame_idx}/{total_frames} frames ({frame_idx // fps}s)", flush=True)

    writer.release()
    print(f"Test video written: {output_path} ({duration_sec}s, {fps}fps)")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sample_conveyor.mp4"
    generate(out)
