"""Safe discovery and execution helpers for Android Debug Bridge (ADB)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

DEFAULT_ADB_TIMEOUT_SECONDS = 10.0
MAX_OUTPUT_BYTES = 65536


@dataclass(frozen=True)
class AdbDevice:
    """A device row reported by adb devices."""

    serial: str
    state: str

    @property
    def is_authorized(self) -> bool:
        """True if the device is authorized and accessible via adb shell."""
        return self.state.strip().lower() == "device"


def find_adb() -> str | None:
    """Return the ADB executable path, if installed."""
    return shutil.which("adb")


def get_adb_version(adb_path: str | None = None) -> str | None:
    """Return the output of adb version, or None if unavailable."""
    executable = adb_path or find_adb()
    if executable is None:
        return None

    try:
        completed = subprocess.run(
            [executable, "version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=DEFAULT_ADB_TIMEOUT_SECONDS,
        )
        if completed.returncode == 0:
            lines = completed.stdout.strip().splitlines()
            return lines[0] if lines else "Installed"
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def list_devices(adb_path: str | None = None) -> list[AdbDevice]:
    """List ADB-visible devices without issuing commands to the devices."""
    executable = adb_path or find_adb()
    if executable is None:
        raise FileNotFoundError(
            "ADB was not found. Install Android Platform Tools and ensure adb is on PATH."
        )

    try:
        completed = subprocess.run(
            [executable, "devices"],
            check=False,
            capture_output=True,
            text=True,
            timeout=DEFAULT_ADB_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ADB device discovery timed out.") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to execute ADB: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown ADB error"
        raise RuntimeError(f"ADB device discovery failed (exit {completed.returncode}): {detail}")

    devices: list[AdbDevice] = []
    lines = completed.stdout.splitlines()
    # Skip any banner or "List of devices attached"
    device_rows = [line for line in lines if not line.startswith("* daemon")]
    if device_rows and "List of devices attached" in device_rows[0]:
        device_rows = device_rows[1:]

    for line in device_rows:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append(AdbDevice(serial=parts[0], state=parts[1]))
    return devices


def run_adb_command(
    serial: str,
    args: list[str],
    timeout: float = DEFAULT_ADB_TIMEOUT_SECONDS,
    max_bytes: int = MAX_OUTPUT_BYTES,
    adb_path: str | None = None,
) -> tuple[int, str, str]:
    """Execute an allowlisted ADB command against a specific device with shell=False.

    Returns (returncode, stdout, stderr).
    """
    executable = adb_path or find_adb()
    if executable is None:
        raise FileNotFoundError("ADB was not found. Install Android Platform Tools.")

    # Explicit argument list without shell interpolation
    cmd = [executable, "-s", serial] + args
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = proc.stdout[:max_bytes]
        stderr = proc.stderr[:max_bytes]
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"ADB command timed out after {timeout} seconds: {' '.join(cmd)}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to invoke ADB command: {exc}") from exc
