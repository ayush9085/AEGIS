"""Safe discovery helpers for Android Debug Bridge (ADB)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class AdbDevice:
    """A device row reported by adb devices."""

    serial: str
    state: str


def find_adb() -> str | None:
    """Return the ADB executable path, if installed."""
    return shutil.which("adb")


def list_devices(adb_path: str | None = None) -> list[AdbDevice]:
    """List ADB-visible devices without issuing commands to the devices."""
    executable = adb_path or find_adb()
    if executable is None:
        raise FileNotFoundError(
            "ADB was not found. Install Android Platform Tools and ensure adb is on PATH."
        )

    completed = subprocess.run(
        [executable, "devices"], check=False, capture_output=True, text=True, timeout=10
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "unknown ADB error"
        raise RuntimeError(f"ADB device discovery failed: {detail}")

    devices: list[AdbDevice] = []
    for line in completed.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append(AdbDevice(serial=parts[0], state=parts[1]))
    return devices
