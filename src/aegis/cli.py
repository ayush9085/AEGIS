"""Command-line interface for AEGIS."""

from __future__ import annotations

import argparse
import platform
import sys

from aegis import __version__
from aegis.adb import find_adb, list_devices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis", description="Read-only-by-default Android systems research toolkit."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("doctor", help="check the local research environment")
    subparsers.add_parser("devices", help="list ADB-visible devices (discovery only)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "doctor":
        adb = find_adb()
        print(f"AEGIS {__version__}")
        print(f"Platform: {platform.system()} {platform.release()}")
        print(f"Python: {platform.python_version()}")
        print(f"ADB: {adb or 'not found (optional; install Android Platform Tools)'}")
        return 0

    if args.command == "devices":
        try:
            devices = list_devices()
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if not devices:
            print("No ADB-visible devices found.")
            return 0
        print("SERIAL\tSTATE")
        for device in devices:
            print(f"{device.serial}\t{device.state}")
        print("\nNote: serials may be sensitive; review output before sharing.")
        return 0

    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
