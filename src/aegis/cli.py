"""Developer-friendly command-line interface for AEGIS."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import webbrowser
from datetime import UTC, datetime
from pathlib import Path

from aegis import __version__
from aegis.adb import find_adb, get_adb_version, list_devices
from aegis.collectors.engine import collect_device_evidence, get_collection_plan
from aegis.redaction import redact_serial
from aegis.reports.html import render_html_report
from aegis.schema import EvidenceReport, validate_evidence_dict


def _color(text: str, code: str) -> str:
    """Apply ANSI color styling if stdout is a TTY and colors are not disabled."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _bold(text: str) -> str:
    return _color(text, "1")


def _green(text: str) -> str:
    return _color(text, "32")


def _cyan(text: str) -> str:
    return _color(text, "36")


def _yellow(text: str) -> str:
    return _color(text, "33")


def _red(text: str) -> str:
    return _color(text, "31")


def _dim(text: str) -> str:
    return _color(text, "2")


def open_in_browser(file_path: Path) -> None:
    """Open an HTML report in the system's default browser."""
    try:
        resolved = file_path.resolve()
        if platform.system() == "Darwin":
            subprocess.run(["open", str(resolved)], check=False)
        else:
            webbrowser.open(resolved.as_uri())
    except OSError:
        pass


def find_latest_evidence(search_root: Path | None = None) -> Path | None:
    """Find the most recently modified evidence.json file under reports/."""
    root = search_root or Path("./reports")
    if not root.is_dir():
        return None
    candidates = list(root.glob("**/evidence.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line argument parser for AEGIS."""
    parser = argparse.ArgumentParser(
        prog="aegis",
        description="AEGIS: Android Exploration, Guardrails, Intelligence & Security (Phase One MVP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quickstart examples:
  aegis doctor                 Check ADB and Python environment
  aegis devices                List connected Android devices
  aegis collect                Auto-detect phone, collect evidence, & render report
  aegis collect --open         Collect and immediately open the HTML report in browser
  aegis report                 Generate report for the most recent collection
  aegis demo --open            View a sample report with synthetic data (no phone needed)
        """,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # menu
    subparsers.add_parser("menu", help="Launch interactive guided menu (easy mode for developers)")

    # doctor
    subparsers.add_parser("doctor", help="Check local environment and ADB setup")

    # devices
    subparsers.add_parser("devices", help="List connected Android devices (safe discovery)")

    # collect
    collect_parser = subparsers.add_parser(
        "collect",
        aliases=["scan"],
        help="Collect read-only system evidence and generate report (auto-detects phone)",
    )
    collect_parser.add_argument(
        "--device",
        default=None,
        metavar="SERIAL",
        help="Target device serial (optional; automatically selects if only 1 device is connected)",
    )
    collect_parser.add_argument(
        "--out",
        default=None,
        metavar="DIR",
        help="Output directory (optional; defaults to ./reports/<device>-<timestamp>)",
    )
    collect_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation (does not bypass safety allowlists)",
    )
    collect_parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the generated HTML report in your browser",
    )

    # report
    report_parser = subparsers.add_parser(
        "report", help="Generate HTML report from an evidence JSON bundle"
    )
    report_parser.add_argument(
        "evidence_file",
        nargs="?",
        default=None,
        metavar="PATH",
        help="Path to evidence.json (optional; defaults to most recent collection)",
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
    report_parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the report in your browser",
    )

    # validate
    validate_parser = subparsers.add_parser(
        "validate", help="Validate an evidence JSON document against the schema"
    )
    validate_parser.add_argument(
        "evidence_file",
        nargs="?",
        default=None,
        metavar="PATH",
        help="Path to evidence.json to validate (defaults to most recent collection)",
    )

    # demo
    demo_parser = subparsers.add_parser(
        "demo", help="Generate and view a demo report using synthetic data (no phone needed)"
    )
    demo_parser.add_argument(
        "--open",
        action="store_true",
        default=True,
        help="Open the demo report in browser (default: true)",
    )

    return parser


def _get_device_model_label(serial: str, state: str) -> str:
    """Safely fetch human-readable manufacturer and model for authorized devices."""
    if state != "device":
        return ""
    try:
        from aegis.adb import run_adb_command

        _, brand, _ = run_adb_command(serial, ["shell", "getprop", "ro.product.brand"], timeout=1.5)
        _, model, _ = run_adb_command(serial, ["shell", "getprop", "ro.product.model"], timeout=1.5)
        _, rel, _ = run_adb_command(serial, ["shell", "getprop", "ro.build.version.release"], timeout=1.5)
        brand = brand.strip()
        model = model.strip()
        rel = rel.strip()
        parts = [p for p in (brand, model) if p]
        name = " ".join(parts)
        if name and rel:
            return f"{name} (Android {rel})"
        if name:
            return name
    except (OSError, RuntimeError, FileNotFoundError):
        return ""
    return ""


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

        # Check connected devices count safely
        try:
            devs = list_devices()
            auth_count = sum(1 for d in devs if d.is_authorized)
            if auth_count > 0:
                print(f"Devices Connected: {auth_count} authorized device{'s' if auth_count > 1 else ''} ready")
            elif devs:
                print("Devices Connected: 1 device detected (needs USB authorization)")
            else:
                print("Devices Connected: 0 detected (plug in phone or run 'aegis demo')")
        except (OSError, RuntimeError, FileNotFoundError):
            print("Devices Connected: None detected")

        print("Status: Environment ready for read-only ADB research.")
        print(f"\n👉 Ready to scan! Run: {_bold('aegis scan')}\n")
    else:
        print("ADB Binary: NOT FOUND")
        print("Diagnostic:")
        print("  Android Platform Tools (adb) are required for device communication.")
        print("  On macOS, install via: brew install android-platform-tools")
        print("  Or download from: https://developer.android.com/tools/releases/platform-tools")
        print("  Ensure 'adb' is available on your system PATH.")
        print(f"\n👉 In the meantime, try our demo report: {_bold('aegis demo')}\n")

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
        print("\n💡 Developer Setup Tip:")
        print("  • Go to Settings > About Phone > tap 'Build Number' 7 times.")
        print("  • Go to Settings > Developer Options > enable 'USB Debugging'.")
        print("  • Look at your phone's screen and accept the 'Allow USB debugging' prompt.")
        print(f"\n👉 To test AEGIS without a physical phone, run: {_bold('aegis demo')}\n")
        return 0

    print("SERIAL\t\tSTATE")
    print("-" * 32)
    has_unauthorized = False
    has_offline = False

    for dev in devices:
        label = _get_device_model_label(dev.serial, dev.state)
        if label:
            print(f"{dev.serial}\t{dev.state}\t{_cyan(label)}")
        else:
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
    print(f"\n👉 To scan this device, run: {_bold('aegis scan')}\n")
    return 0


def select_target_device(requested_serial: str | None) -> str | None:
    """Resolve target device serial: requested, auto-selected, or interactive choice."""
    try:
        devices = list_devices()
    except (FileNotFoundError, RuntimeError) as exc:
        print(_red(f"error: {exc}"), file=sys.stderr)
        return None

    if requested_serial:
        return requested_serial

    if not devices:
        print(_red("error: No Android devices detected via ADB."), file=sys.stderr)
        print("Please plug in your phone, enable USB debugging, and verify with 'aegis devices'.", file=sys.stderr)
        print("\n💡 Quick Setup Guide:", file=sys.stderr)
        print("   1. Connect phone via USB data cable.", file=sys.stderr)
        print("   2. Turn on Developer Options: Settings > About Phone > tap 'Build Number' 7 times.", file=sys.stderr)
        print("   3. Turn on USB Debugging: Settings > Developer Options > USB Debugging.", file=sys.stderr)
        print("   4. Unlock phone screen and tap 'Allow USB debugging'.", file=sys.stderr)
        print(f"\n👉 Want to explore AEGIS without a phone? Run: {_bold('aegis demo')}\n", file=sys.stderr)
        return None

    authorized = [d for d in devices if d.is_authorized]
    if not authorized:
        first = devices[0]
        print(_yellow(f"error: Found device '{redact_serial(first.serial)}' but state is '{first.state}'."), file=sys.stderr)
        print("Please unlock your phone screen and tap 'Allow' on the USB debugging prompt.", file=sys.stderr)
        print(f"Then run '{_bold('aegis scan')}' again.\n", file=sys.stderr)
        return None

    if len(authorized) == 1:
        chosen = authorized[0].serial
        label = _get_device_model_label(chosen, "device")
        label_str = f" ({label})" if label else ""
        print(f"📱 {_green('Auto-selected connected device:')} {_bold(redact_serial(chosen))}{label_str}")
        return chosen

    # Multiple devices: prompt user
    print(_bold("\nMultiple authorized devices found. Please select one:"))
    for idx, dev in enumerate(authorized, 1):
        label = _get_device_model_label(dev.serial, dev.state)
        label_str = f" - {label}" if label else ""
        print(f"  [{idx}] Serial: {dev.serial}{label_str}")
    try:
        choice = input(f"Select device [1-{len(authorized)}]: ").strip()
        idx_choice = int(choice) - 1
        if 0 <= idx_choice < len(authorized):
            return authorized[idx_choice].serial
    except (ValueError, KeyboardInterrupt, EOFError):
        pass

    print(_red("Selection cancelled."), file=sys.stderr)
    return None


def handle_collect(
    device_serial: str | None,
    out_dir: str | None,
    non_interactive: bool,
    open_report: bool = False,
) -> int:
    """Execute the collect command with smart defaults, plan preview, and HTML generation."""
    resolved_serial = select_target_device(device_serial)
    if not resolved_serial:
        return 2

    # Default output directory if not provided
    if not out_dir:
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        safe_tag = resolved_serial[:4] if len(resolved_serial) >= 4 else "android"
        out_dir = f"./reports/device-{safe_tag}-{ts}"

    plan = get_collection_plan()

    print(_bold("\n🛡️  AEGIS Read-Only Inspection Plan"))
    print(_dim("──────────────────────────────────────────────────"))
    print(f"  Target Handset:  {_cyan(redact_serial(resolved_serial))}")
    print(f"  Allowlist Scope: {_green(f'{len(plan)} safe read-only probes')}")
    print("  Categories:      • Hardware identity (Brand, Model, Product, Board)")
    print("                   • Android OS & Build (Release, API Level, Security Patch, Build ID)")
    print("                   • Kernel metadata (uname release)")
    print("                   • Verified Boot flags (AVB state, dm-verity, flash lock)")
    print("  Safety Rules:    NO private data, NO writes, NO flashing, NO rooting.")
    print(_dim("──────────────────────────────────────────────────"))

    if not non_interactive:
        try:
            confirm = input(f"Proceed with read-only collection? [{_bold('Y')}/n]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(_yellow("\nCollection aborted by user."), file=sys.stderr)
            return 1
        if confirm and confirm not in ("y", "yes"):
            print(_yellow("Collection aborted by user."), file=sys.stderr)
            return 1
    else:
        print(_dim("Proceeding (consent specified via --yes flag)."))

    print("\nExecuting allowlisted probes...")
    try:
        report = collect_device_evidence(serial=resolved_serial, consent_given=True)
    except (FileNotFoundError, RuntimeError, PermissionError) as exc:
        print(_red(f"error: {exc}"), file=sys.stderr)
        return 2

    # Save evidence.json
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    evidence_file = out_path / "evidence.json"
    evidence_file.write_text(report.to_json(indent=2), encoding="utf-8")

    # Automatically generate report.html alongside evidence.json
    html_text = render_html_report(report)
    report_file = out_path / "report.html"
    report_file.write_text(html_text, encoding="utf-8")

    print(_green("\nCollection successful!"))
    print(_dim("──────────────────────────────────────────────────"))
    dev_str = f"{report.device.manufacturer or ''} {report.device.model or ''}".strip() or "Android Device"
    os_str = f"Android {report.device.android_version or '?'} (API {report.device.sdk_version or '?'})"
    obs_str = _green(f"{report.summary.observed} observed")
    uns_str = _yellow(f"{report.summary.unsupported} unsupported")
    err_str = _red(f"{report.summary.error} errors")

    print(f"  Device:     {_bold(dev_str)}")
    print(f"  OS/Build:   {os_str}")
    print(f"  Findings:   {obs_str}, {uns_str}, {err_str}")
    print(_dim("──────────────────────────────────────────────────"))
    print(f"  📄 Evidence JSON: {_cyan(str(evidence_file))}")
    print(f"  📊 HTML Report:   {_cyan(str(report_file))}")
    print(_dim("──────────────────────────────────────────────────"))
    print(f"👉 View report: {_bold(f'open {report_file}')}\n")

    if open_report:
        open_in_browser(report_file)

    return 0


def handle_report(evidence_path: str | None, fmt: str, out_file: str | None, open_report: bool = False) -> int:
    """Generate a self-contained HTML report from evidence JSON."""
    if not evidence_path:
        latest = find_latest_evidence()
        if not latest:
            print(_red("error: No evidence.json found. Run 'aegis collect' first or specify a path."), file=sys.stderr)
            return 2
        ev_path = latest
        print(_dim(f"Auto-selected latest evidence: {ev_path}"))
    else:
        ev_path = Path(evidence_path)

    if not ev_path.is_file():
        print(_red(f"error: Evidence file not found: {ev_path}"), file=sys.stderr)
        return 2

    try:
        content = ev_path.read_text(encoding="utf-8")
        report = EvidenceReport.from_json(content)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OSError) as exc:
        print(_red(f"error: Failed to parse evidence document: {exc}"), file=sys.stderr)
        return 2

    if fmt != "html":
        print(_red(f"error: Unsupported format '{fmt}'. Only 'html' is supported in Phase One."), file=sys.stderr)
        return 2

    html_text = render_html_report(report)

    dest = Path(out_file) if out_file else ev_path.parent / "report.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html_text, encoding="utf-8")

    print(_green(f"Report successfully generated: {dest}"))
    print(f"👉 View in browser: {_bold(f'open {dest}')}")

    if open_report:
        open_in_browser(dest)

    return 0


def handle_validate(evidence_path: str | None) -> int:
    """Validate an evidence file against the schema."""
    if not evidence_path:
        latest = find_latest_evidence()
        if not latest:
            print(_red("error: No evidence.json found to validate. Run 'aegis collect' first."), file=sys.stderr)
            return 2
        ev_path = latest
        print(_dim(f"Auto-selected latest evidence: {ev_path}"))
    else:
        ev_path = Path(evidence_path)

    if not ev_path.is_file():
        print(_red(f"error: Evidence file not found: {ev_path}"), file=sys.stderr)
        return 2

    try:
        data = json.loads(ev_path.read_text(encoding="utf-8"))
        validate_evidence_dict(data)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OSError) as exc:
        print(_red(f"error: Validation failed: {exc}"), file=sys.stderr)
        return 2

    version = data.get("schema_version")
    obs_count = len(data.get("observations", []))
    print(_green(f"Validation passed: Valid AEGIS evidence document (Schema v{version}, {obs_count} observations)."))
    return 0


def handle_demo(open_report: bool = True) -> int:
    """Generate and view a demo report using synthetic fixture data."""
    fixture = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "sample_evidence.json"
    if not fixture.is_file():
        # Fallback to local check
        fixture = Path("./tests/fixtures/sample_evidence.json")

    if not fixture.is_file():
        print(_red(f"error: Sample fixture not found at {fixture}"), file=sys.stderr)
        return 2

    demo_dir = Path("./reports/demo")
    demo_dir.mkdir(parents=True, exist_ok=True)
    out_report = demo_dir / "sample_report.html"

    report = EvidenceReport.from_json(fixture.read_text(encoding="utf-8"))
    out_report.write_text(render_html_report(report), encoding="utf-8")

    print(_green("\nDemo report generated successfully!"))
    print(_dim("──────────────────────────────────────────────────"))
    print(f"  📄 Source: {_cyan('Synthetic Test Fixture (Samsung Galaxy M11 sample)')}")
    print(f"  📊 Output: {_cyan(str(out_report))}")
    print(_dim("──────────────────────────────────────────────────"))
    print(f"👉 View in browser: {_bold(f'open {out_report}')}\n")

    if open_report:
        open_in_browser(out_report)

    return 0


def handle_interactive_menu() -> int:
    """Present a friendly, guided menu for local developers."""
    show_menu = True
    while True:
        if show_menu:
            print(_bold("\n🛡️  Welcome to AEGIS"))
            print(_dim(f"   Android Security & Firmware Reconnaissance (v{__version__})"))
            print(_dim("   Zero-modification, read-only inspection toolkit for developers.\n"))

            print(_bold("What would you like to do?"))
            print(f"  [{_cyan('1')}] 🚀 {_bold('Scan connected phone')}   - Auto-detect, collect evidence & view report")
            print(f"  [{_cyan('2')}] 📱 {_bold('List connected devices')} - See connected phones and authorization status")
            print(f"  [{_cyan('3')}] 🩺 {_bold('Run environment doctor')} - Check ADB, Python, and system prerequisites")
            print(f"  [{_cyan('4')}] 🧪 {_bold('Preview demo report')}    - Explore report UI with sample data (no phone needed)")
            print(f"  [{_cyan('5')}] 📖 {_bold('Show command help')}     - View all commands, flags, and options")
            print(f"  [{_cyan('0')}] 🚪 {_dim('Exit')}\n")

        try:
            prompt = (
                f"Enter choice [{_bold('1')}-5, or 0 to exit]: "
                if show_menu
                else f"Enter next choice [{_bold('1')}-5, or 0 to exit] (Enter for menu): "
            )
            choice = input(prompt).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            return 0

        # In non-interactive test environments, avoid infinite looping
        is_interactive = sys.stdin.isatty() and sys.stdout.isatty()

        if choice in ("0", "q", "exit", "quit"):
            print("Goodbye!")
            return 0
        elif not choice and not show_menu:
            show_menu = True
            continue
        elif not choice or choice == "1":
            handle_collect(device_serial=None, out_dir=None, non_interactive=False, open_report=True)
            show_menu = False
        elif choice == "2":
            handle_devices()
            show_menu = False
        elif choice == "3":
            handle_doctor()
            show_menu = False
        elif choice == "4":
            handle_demo(open_report=True)
            show_menu = False
        elif choice == "5":
            build_parser().print_help()
            show_menu = False
        else:
            print(_yellow(f"\nInvalid option '{choice}'. Please select 1-5, or 0 to exit.\n"))
            show_menu = True

        if not is_interactive:
            return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        if sys.stdin.isatty() and sys.stdout.isatty():
            return handle_interactive_menu()
        parser.print_help()
        return 0

    if args.command == "menu":
        return handle_interactive_menu()

    if args.command == "doctor":
        return handle_doctor()

    if args.command == "devices":
        return handle_devices()

    if args.command in ("collect", "scan"):
        return handle_collect(
            device_serial=args.device,
            out_dir=args.out,
            non_interactive=args.yes,
            open_report=args.open,
        )

    if args.command == "report":
        return handle_report(
            evidence_path=args.evidence_file,
            fmt=args.format,
            out_file=args.out,
            open_report=args.open,
        )

    if args.command == "validate":
        return handle_validate(evidence_path=args.evidence_file)

    if args.command == "demo":
        return handle_demo(open_report=args.open)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
