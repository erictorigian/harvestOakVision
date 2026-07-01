"""
Hardware detection and optimization profile selection.

Returns one of: 'pi_coral' | 'pi_cpu' | 'imac' | 'generic'
"""
from __future__ import annotations

import logging
import os
import platform
import subprocess

logger = logging.getLogger("harvest_oak.hardware")


def _check_coral_usb() -> bool:
    """Check if a Google Coral USB TPU is attached."""
    try:
        result = subprocess.run(
            ["lsusb"], capture_output=True, text=True, timeout=3
        )
        # Coral USB vendor ID: 1a6e (Global Unichip) or 18d1 (Google)
        return "1a6e" in result.stdout or "18d1:9302" in result.stdout
    except Exception:
        return False


def _available_ram_mb() -> int:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 8192  # assume plenty if we can't read


def detect_hardware() -> dict:
    arch = platform.machine().lower()
    is_arm = arch in ("aarch64", "arm64", "armv7l")
    ram_mb = _available_ram_mb()

    if is_arm:
        has_coral = _check_coral_usb()
        profile = "pi_coral" if has_coral else "pi_cpu"
    elif "x86_64" in arch or "amd64" in arch:
        # Check for iMac vs generic Linux server
        uname = platform.uname()
        is_mac_host = "darwin" in uname.system.lower() or os.path.exists("/proc/sys/kernel/ostype") is False
        profile = "imac" if (ram_mb > 4096) else "generic"
    else:
        profile = "generic"

    config = _profile_config(profile)
    logger.info(
        f"Hardware detected: arch={arch} ram={ram_mb}MB profile={profile} "
        f"fps={config['detection_fps']} width={config['frame_width']}"
    )
    return {"profile": profile, "arch": arch, "ram_mb": ram_mb, **config}


def _profile_config(profile: str) -> dict:
    configs = {
        "pi_coral": {
            "detection_fps": 10,
            "frame_width": 640,
            "use_coral": True,
            "cv2_threads": 2,
            "use_yolo": True,
            "yolo_model": "yolov8n_edgetpu.tflite",
        },
        "pi_cpu": {
            "detection_fps": 5,
            "frame_width": 640,
            "use_coral": False,
            "cv2_threads": 2,
            "use_yolo": False,   # MOG2 only on CPU Pi — too slow for YOLO
            "yolo_model": None,
        },
        "imac": {
            "detection_fps": 10,
            "frame_width": 1280,
            "use_coral": False,
            "cv2_threads": 4,
            "use_yolo": False,   # MOG2 is sufficient and more robust for this use case
            "yolo_model": None,
        },
        "generic": {
            "detection_fps": 8,
            "frame_width": 960,
            "use_coral": False,
            "cv2_threads": 2,
            "use_yolo": False,
            "yolo_model": None,
        },
    }
    return configs.get(profile, configs["generic"])
