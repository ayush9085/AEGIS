"""Parser for Android build.prop and text property files."""

from __future__ import annotations

from pathlib import Path

from aegis.firmware.models import FirmwareFinding

PARSER_NAME = "aegis_prop_parser"
PARSER_VERSION = "0.1.0"

MAX_PROP_READ_BYTES = 2 * 1024 * 1024  # 2 MB limit

INTERESTING_PROPS = {
    "ro.build.version.release": ("OS Release Version", "os_metadata"),
    "ro.build.version.sdk": ("SDK API Level", "os_metadata"),
    "ro.build.version.security_patch": ("Declared Security Patch", "os_metadata"),
    "ro.build.id": ("Build ID", "os_metadata"),
    "ro.build.fingerprint": ("Build Fingerprint", "os_metadata"),
    "ro.product.manufacturer": ("Manufacturer", "os_metadata"),
    "ro.product.model": ("Model Identifier", "os_metadata"),
    "ro.product.name": ("Product Name", "os_metadata"),
    "ro.product.device": ("Device Codename", "os_metadata"),
    "ro.product.board": ("Board Platform", "os_metadata"),
    "ro.boot.vbmeta.device_state": ("Declared VBMeta State", "security_metadata"),
    "ro.boot.flash.locked": ("Declared Flash Lock", "security_metadata"),
    "ro.boot.verifiedbootstate": ("Declared Verified Boot State", "security_metadata"),
}


def parse_build_prop(
    file_path: Path,
    rel_path: str,
) -> tuple[str, list[FirmwareFinding], list[str], str | None]:
    """Parse Android build.prop key-value pairs safely with bounds."""
    findings: list[FirmwareFinding] = []
    warnings: list[str] = []

    try:
        file_size = file_path.stat().st_size
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to stat file: {exc}"

    if file_size > MAX_PROP_READ_BYTES:
        warnings.append(
            f"Property file size {file_size} exceeds limit {MAX_PROP_READ_BYTES}. Reading first 2 MB."
        )

    try:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            content = f.read(MAX_PROP_READ_BYTES)
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to read file: {exc}"

    extracted_count = 0
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()

        if key in INTERESTING_PROPS:
            label, category = INTERESTING_PROPS[key]
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:prop:{key}",
                    category=category,
                    key=f"build_prop.{key}",
                    label=label,
                    status="observed",
                    value=val,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                    caveat="Static property declared in userspace build.prop.",
                )
            )
            extracted_count += 1

    if extracted_count == 0:
        warnings.append("No standard Android build properties matched in file.")

    return "observed", findings, warnings, None
