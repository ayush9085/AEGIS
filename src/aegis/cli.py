"""Command-line interface for AEGIS."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from aegis import __version__
from aegis.adb import find_adb, get_adb_version, list_devices
from aegis.collectors.engine import collect_device_evidence, get_collection_plan
from aegis.reports.html import render_html_report
from aegis.schema import EvidenceReport, validate_evidence_dict


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line argument parser for AEGIS."""
    parser = argparse.ArgumentParser(
        prog="aegis",
        description="AEGIS: Android Exploration, Guardrails, Intelligence & Security (Phase One MVP)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # doctor
    subparsers.add_parser("doctor", help="Inspect local environment and ADB setup")

    # devices
    subparsers.add_parser("devices", help="List ADB-visible devices (read-only discovery)")

    # collect
    collect_parser = subparsers.add_parser(
        "collect", help="Execute read-only allowlisted property collection on target device"
    )
    collect_parser.add_argument(
        "--device",
        required=True,
        metavar="SERIAL",
        help="Target device serial (explicit selection required; see 'aegis devices')",
    )
    collect_parser.add_argument(
        "--out",
        required=True,
        metavar="DIR",
        help="Output directory path where evidence.json will be saved",
    )
    collect_parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm consent non-interactively (does not bypass allowlist or device checks)",
    )

    # report
    report_parser = subparsers.add_parser(
        "report", help="Generate self-contained report from an evidence JSON bundle"
    )
    report_parser.add_argument(
        "evidence_file",
        metavar="PATH",
        help="Path to evidence.json",
    )
    report_parser.add_argument(
        "--format",
        choices=["html"],
        default="html",
        help="Report output format (default: html)",
    )
    report_parser.add_argument(
        "--out",
        metavar="FILE",
        default=None,
        help="Output HTML file path (default: <evidence_dir>/report.html)",
    )

    # validate
    validate_parser = subparsers.add_parser(
        "validate", help="Validate an evidence JSON document against the schema"
    )
    validate_parser.add_argument(
        "evidence_file",
        metavar="PATH",
        help="Path to evidence.json to validate",
    )

    return parser


def handle_doctor() -> int:
    """Execute the doctor diagnostic command."""
    adb_path = find_adb()
    adb_version_str = get_adb_version(adb_path) if adb_path else None

    print(f"AEGIS Version: {__version__}")
    print(f"Host Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()} ({sys.executable})")

    if adb_path:
        print(f"ADB Binary: {adb_path}")
        print(f"ADB Version: {adb_version_str or 'detected'}")
        print("Status: Environment ready for read-only ADB research.")
    else:
        print("ADB Binary: NOT FOUND")
        print("Diagnostic:")
        print("  Android Platform Tools (adb) are required for device communication.")
        print("  On macOS, install via: brew install android-platform-tools")
        print("  Or download from: https://developer.android.com/tools/releases/platform-tools")
        print("  Ensure 'adb' is available on your system PATH.")

    return 0


def handle_devices() -> int:
    """Execute the devices discovery command."""
    try:
        devices = list_devices()
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not devices:
        print("No ADB-visible devices found.")
        print("Check:")
        print("  1. Device is connected via a data-capable USB cable.")
        print("  2. USB debugging is enabled in Developer Options.")
        return 0

    print("SERIAL\t\tSTATE")
    print("-" * 32)
    has_unauthorized = False
    has_offline = False

    for dev in devices:
        print(f"{dev.serial}\t{dev.state}")
        if dev.state == "unauthorized":
            has_unauthorized = True
        elif dev.state == "offline":
            has_offline = True

    if has_unauthorized:
        print("\nNotice: One or more devices are 'unauthorized'. Unlock the screen and accept the USB prompt.")
    if has_offline:
        print("\nNotice: One or more devices are 'offline'. Re-plug the USB cable or restart ADB.")

    print("\nNote: serial numbers may be sensitive; review before public sharing.")
    return 0


def handle_collect(device_serial: str, out_dir: str, non_interactive: bool) -> int:
    """Execute the collect command with plan preview and consent gate."""
    plan = get_collection_plan()

    print("=== AEGIS Collection Plan Preview ===")
    print(f"Target Device: {device_serial}")
    print(f"Total Allowlisted Probes: {len(plan)}")
    print("Method: Read-only ADB commands (shell getprop / uname)")
    print("Scope: Fixed system build, version, and boot properties only.")
    print("Security: NO private data, NO flashing, NO writes, NO bootloader unlocking.\n")

    print(f"{'PROBE KEY':<28} {'METHOD':<35} {'DESCRIPTION'}")
    print("-" * 90)
    for p in plan:
        print(f"{p['key']:<28} {p['method']:<35} {p['description']}")
    print("-" * 90)

    if not non_interactive:
        try:
            confirm = input("\nProceed with read-only collection? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCollection aborted by user.", file=sys.stderr)
            return 1
        if confirm not in ("y", "yes"):
            print("Collection aborted by user.", file=sys.stderr)
            return 1
    else:
        print("\nProceeding (consent specified via --yes flag).")

    print("\nExecuting allowlisted probes...")
    try:
        report = collect_device_evidence(serial=device_serial, consent_given=True)
    except (FileNotFoundError, RuntimeError, PermissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Save to requested directory
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    evidence_file = out_path / "evidence.json"

    evidence_file.write_text(report.to_json(indent=2), encoding="utf-8")

    print("\nCollection successful!")
    print(f"Evidence file saved to: {evidence_file}")
    print(f"Summary: {report.summary.observed} observed, {report.summary.unsupported} unsupported, "
          f"{report.summary.inaccessible} inaccessible, {report.summary.error} errors.")
    return 0


def handle_report(evidence_path: str, fmt: str, out_file: str | None) -> int:
    """Generate a self-contained HTML report from evidence JSON."""
    ev_path = Path(evidence_path)
    if not ev_path.is_file():
        print(f"error: Evidence file not found: {evidence_path}", file=sys.stderr)
        return 2

    try:
        content = ev_path.read_text(encoding="utf-8")
        report = EvidenceReport.from_json(content)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OSError) as exc:
        print(f"error: Failed to parse evidence document: {exc}", file=sys.stderr)
        return 2

    if fmt != "html":
        print(f"error: Unsupported format '{fmt}'. Only 'html' is supported in Phase One.", file=sys.stderr)
        return 2

    html_text = render_html_report(report)

    dest = Path(out_file) if out_file else ev_path.parent / "report.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html_text, encoding="utf-8")

    print(f"Report successfully generated: {dest}")
    return 0


def handle_validate(evidence_path: str) -> int:
    """Validate an evidence file against the schema."""
    ev_path = Path(evidence_path)
    if not ev_path.is_file():
        print(f"error: Evidence file not found: {evidence_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(ev_path.read_text(encoding="utf-8"))
        validate_evidence_dict(data)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OSError) as exc:
        print(f"error: Validation failed: {exc}", file=sys.stderr)
        return 2

    version = data.get("schema_version")
    obs_count = len(data.get("observations", []))
    print(f"Validation passed: Valid AEGIS evidence document (Schema v{version}, {obs_count} observations).")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "doctor":
        return handle_doctor()

    if args.command == "devices":
        return handle_devices()

    if args.command == "collect":
        return handle_collect(
            device_serial=args.device,
            out_dir=args.out,
            non_interactive=args.yes,
        )

    if args.command == "report":
        return handle_report(
            evidence_path=args.evidence_file,
            fmt=args.format,
            out_file=args.out,
        )

    if args.command == "validate":
        return handle_validate(evidence_path=args.evidence_file)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
