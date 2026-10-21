"""Redaction helpers to protect sensitive device and environment identifiers."""

from __future__ import annotations

import re

# Regex for common sensitive patterns
# IMEI: 14 to 16 continuous digits
IMEI_PATTERN = re.compile(r"\b\d{14,16}\b")
# MAC addresses: 6 pairs of hex digits separated by colon or hyphen
MAC_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")


def redact_serial(serial: str) -> str:
    """Mask a hardware serial or ADB identifier for safe public display."""
    clean = serial.strip()
    if not clean:
        return "[EMPTY]"
    if clean.upper() in {"EMULATOR-5554", "EMULATOR-5556", "UNKNOWN", "NONE"}:
        return clean
    if len(clean) <= 4:
        return "[REDACTED]"
    # Show first 2 and last 2 characters, mask middle
    return f"{clean[:2]}***{clean[-2:]}"


def redact_sensitive_text(text: str, known_serials: list[str] | None = None) -> str:
    """Scrub sensitive identifiers (serials, IMEIs, MACs) from a text string."""
    if not text:
        return text

    redacted = text
    if known_serials:
        for s in sorted(known_serials, key=len, reverse=True):
            if s and len(s) > 2:
                redacted = redacted.replace(s, redact_serial(s))

    # Redact IMEIs
    redacted = IMEI_PATTERN.sub("[REDACTED-IMEI]", redacted)
    # Redact MAC addresses
    redacted = MAC_PATTERN.sub("[REDACTED-MAC]", redacted)

    return redacted
