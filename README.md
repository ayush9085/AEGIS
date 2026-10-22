# AEGIS

**Android Exploration, Guardrails, Intelligence & Security**

> Exploring the Android boot chain, kernel architecture, firmware internals, and verified-boot security through device-specific systems research.

AEGIS is an open-source, read-only-by-default toolkit for documenting Android device properties and organizing reproducible evidence. The initial research target is the Samsung Galaxy M11 (its exact model variant, region, firmware build, and Android version are discovered directly from the handset).

---

## Status: Phase One MVP

AEGIS Phase One is a working, tested command-line toolkit for safe Android device reconnaissance, schema-validated evidence collection, and self-contained HTML reporting.

### Implemented Commands:
* `aegis --help` / `aegis --version`: Display documentation and version info.
* `aegis doctor`: Verify host operating system, Python runtime, and Android Debug Bridge (ADB) installation.
* `aegis devices`: Enumerate attached ADB devices with status diagnostics (handling authorized, unauthorized, and offline states).
* `aegis collect --device <serial> --out <dir>`: Execute bounded, read-only, consent-gated allowlist probes and output `evidence.json`.
* `aegis report <path/to/evidence.json> --format html [--out <file>]`: Render a self-contained, accessible HTML report with zero external CDN dependencies and full XSS mitigation.
* `aegis validate <path/to/evidence.json>`: Verify an evidence JSON document against the schema specification.

---

## Safety & Privacy Principles

> **WARNING: DO NOT UNLOCK THE BOOTLOADER.**  
> AEGIS does **NOT** require unlocking the bootloader, rooting the device, flashing custom recoveries, or entering Download Mode. Unlocking a bootloader wipes user data, permanently alters security state (such as Samsung Knox warranty bit 0x1), and compromises platform integrity.

* **Read-Only by Design**: All device probes use narrow, fixed allowlists (`getprop` and `uname`). No write commands, partition dumps, or configuration changes are executed.
* **Explicit User Consent**: Device probing requires explicit user confirmation of the planned inspection commands (or explicit `--yes` flag).
* **Controlled Status Vocabulary**: Checks are explicitly labeled as `observed`, `unsupported`, `inaccessible`, `not_applicable`, `unknown`, or `error`. Missing fields are never assumed to mean a feature is disabled.
* **No False Security Verdicts**: AEGIS **never** renders a single binary "SECURE" or "COMPROMISED" badge. Findings are presented as factual ground-truth observations.
* **Automatic Identifier Redaction**: Hardware serial numbers and sensitive patterns (such as IMEIs or MAC addresses) are redacted by default in public-facing reports.
* **Local-First**: Evidence documents and reports remain on the local workstation. No telemetry or cloud uploads.

---

## Quick Start on macOS

### Prerequisites
1. **Python 3.11+**: Ensure Python 3.11 or 3.12 is installed (`python3 --version`).
2. **Android Platform Tools (ADB)**:
   Install via Homebrew:
   ```bash
   brew install android-platform-tools
   ```
   Or download the official standalone tools directly from [Google Android Platform Tools](https://developer.android.com/tools/releases/platform-tools).

### Installation
Clone the repository and install in editable development mode:
```bash
git clone https://github.com/ayush9085/AEGIS.git
cd AEGIS
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Handset Preparation (e.g. Samsung Galaxy M11)
1. Open **Settings** → **About phone** → **Software information**.
2. Tap **Build number** 7 times to enable **Developer options**.
3. Go back to **Settings** → **Developer options** and turn on **USB debugging**.
4. Connect the phone to your Mac using a known data-capable USB-C / USB-A cable.
5. On the phone display, tap **Allow** on the RSA authorization prompt ("Always allow from this computer").

---

---

## Usage Workflow

### 🚀 Easiest Quickstart (Guided Menu)
Just run `./run.sh` or `aegis` in your terminal:
```bash
./run.sh
```
This opens the guided developer launcher:
```
🛡️  Welcome to AEGIS
   Android Security & Firmware Reconnaissance (v0.1.0)

What would you like to do?
  [1] 🚀 Scan connected phone   - Auto-detect, collect evidence & view report
  [2] 📱 List connected devices - See connected phones and authorization status
  [3] 🩺 Run environment doctor - Check ADB, Python, and system prerequisites
  [4] 🧪 Preview demo report    - Explore report UI with sample data (no phone needed)
  [5] 📖 Show command help     - View all commands, flags, and options
  [0] 🚪 Exit
```

---

### ⚡ Direct One-Step Scan
Connect your Android phone via USB and run:
```bash
./run.sh scan
```
AEGIS will automatically:
1. Detect your connected phone and model
2. Run all 15 read-only security & boot probes
3. Save `evidence.json` and generate `report.html`
4. Open the report directly in your browser

---

### 🛠️ Individual Commands

```bash
# 1. Check your setup & ADB
./run.sh doctor

# 2. See connected Android devices (with human-readable model & Android version)
./run.sh devices

# 3. Collect evidence (auto-detects phone if 1 is connected)
./run.sh collect

# 4. View sample report without a phone
./run.sh demo

# 5. Run test suite & linter
./run.sh test
```

*Advanced manual flags (e.g. `--device <serial>`, `--out <dir>`, `--yes`) are supported for scripting and CI pipelines.*

---

## Fixed Collection Allowlist

AEGIS Phase One queries only documented, unprivileged properties:
* **Hardware & Model**: `ro.product.manufacturer`, `ro.product.model`, `ro.product.name`, `ro.product.device`
* **Software Build**: `ro.build.version.release`, `ro.build.version.sdk`, `ro.build.version.security_patch`, `ro.build.id`, `ro.build.fingerprint`
* **Kernel Metadata**: `uname -r`
* **Boot & Verified Boot Indicators**: `ro.bootloader`, `ro.boot.verifiedbootstate`, `ro.boot.vbmeta.device_state`, `ro.boot.flash.locked`, `ro.boot.veritymode`

---

## Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `ADB Binary: NOT FOUND` | ADB is not in system `PATH` | Run `brew install android-platform-tools` or add platform-tools directory to your shell configuration (`~/.zshrc`). |
| Device status `unauthorized` | Host RSA key unaccepted | Unlock the handset screen and accept the USB Debugging permission prompt. |
| Device status `offline` | USB connection handshake drop | Disconnect and reconnect the USB cable, or run `adb kill-server && adb start-server`. |
| `Device ... not found` | Serial mismatch | Run `aegis devices` to verify the exact serial string currently recognized by ADB. |
| Property status `unsupported` | Property not exposed by OEM | This is expected behavior; older Android releases or OEM builds omit certain AVB properties. |

---

## Development & Testing

Run all unit tests and linting locally:
```bash
# Run test suite
python3 -m pytest

# Run Ruff linter
python3 -m ruff check .
```

All 59 unit tests run against synthetic and mocked fixtures without requiring a physical handset or ADB daemon.

---

## Repository Map

* [src/aegis/](file:///Users/ayush9085/Documents/AEGIS/src/aegis): Core package containing CLI, ADB helpers, schema, redaction, collectors, and reporting engines.
* [tests/](file:///Users/ayush9085/Documents/AEGIS/tests): Unit and integration test suites with synthetic fixtures.
* [docs/architecture.md](file:///Users/ayush9085/Documents/AEGIS/docs/architecture.md): Architectural design and subsystem breakdown.
* [docs/threat-model.md](file:///Users/ayush9085/Documents/AEGIS/docs/threat-model.md): Security boundary, threat analysis, and risk mitigations.
* [docs/device-support.md](file:///Users/ayush9085/Documents/AEGIS/docs/device-support.md): Device compatibility matrix and research scope.
* [docs/evidence-schema.md](file:///Users/ayush9085/Documents/AEGIS/docs/evidence-schema.md): Data dictionary, schema versioning, and status vocabulary.
* [docs/phase-one-validation.md](file:///Users/ayush9085/Documents/AEGIS/docs/phase-one-validation.md): Detailed verification report and command audit log.

---

## License

MIT. See [LICENSE](file:///Users/ayush9085/Documents/AEGIS/LICENSE).
