# AEGIS

**Android Exploration, Guardrails, Intelligence & Security**

> Exploring the Android boot chain, kernel architecture, firmware internals, and verified-boot security through device-specific systems research.

AEGIS is an open-source, read-only-by-default toolkit for documenting Android device properties and organizing reproducible evidence. The initial research target is the Samsung Galaxy M11; its exact model, region, firmware build, and Android version must be verified before drawing device-specific conclusions.

## Status

**Early scaffold — not a firmware analyzer yet.** The current MVP checks the local environment and discovers Android Debug Bridge (ADB) devices. Collection, report generation, and diffing are planned, not implemented.

## Safety principles

- No bootloader unlocking, flashing, rooting, partition writes, or security-control bypasses.
- No destructive commands or commands that modify device state.
- Explicit consent and a reviewed collection plan before collecting device information.
- Redact serial numbers, account identifiers, and sensitive data before sharing reports.
- Distinguish observed facts, inferences, and unknowns.
- Only analyze devices and firmware you own or are authorized to research.

## Quick start

Requirements: Python 3.11+ and optionally Android Platform Tools (ADB).

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
    aegis --help
    aegis doctor
    aegis devices
    python -m pytest

If ADB is installed, enable Developer options and USB debugging on your test device, connect it, and authorize the computer on the device. AEGIS currently only lists ADB-visible devices; it does not run shell commands on the phone.

## Planned commands

- aegis collect — opt-in, read-only collection with a preview of fields first.
- aegis report — create a local evidence report with provenance and redaction.
- aegis diff — compare saved reports without contacting a device.

These are roadmap items and are not implemented in the current scaffold.

## Research questions

1. What boot-chain and verified-boot properties can be documented through public documentation and authorized, read-only observations?
2. Which observations are device/build-specific versus general Android platform behavior?
3. How can evidence be reproducible, auditable, and privacy-preserving?
4. What limitations prevent user-space observations from proving firmware integrity?

## Repository map

- src/aegis/ — Python package and CLI
- tests/ — automated tests
- docs/ — architecture, device support, and threat model
- .github/workflows/ — continuous integration

## Contributing

Read the architecture notes, device support policy, and threat model before contributing. Safety regressions and undocumented collection behavior are blockers.

## Disclaimer

AEGIS is an educational research tool, not a security certification tool. A clean report does not prove a device is uncompromised. Android behavior varies by manufacturer, model, region, firmware build, and configuration.

## License

MIT. See LICENSE.
