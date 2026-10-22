# AEGIS

**Android Exploration, Guardrails, Intelligence & Security**

> Exploring the Android boot chain, kernel architecture, firmware internals, and verified-boot security through device-specific systems research.

AEGIS is an open-source, read-only-by-default toolkit for documenting Android device properties and organizing reproducible evidence. The initial research target is the Samsung Galaxy M11 (its exact model variant, region, firmware build, and Android version are discovered directly from the handset).

---

## Status: Release Candidate v0.1.0-rc1 (Phases 1–6 Complete)

AEGIS has completed all foundational development phases (1–6):
* **Phase 1: Read-Only Reconnaissance**: Unprivileged 15-property allowlist collection, consent gating, identifier redaction, and accessible HTML reporting.
* **Phase 2: Snapshots & Semantic Diffs**: Versioned evidence snapshots, canonical SHA-256 hashing, and deterministic semantic diffs.
* **Phase 3: Offline Firmware Intelligence**: Safe, bounds-checked static parsing for boot.img, vendor_boot, sparse images, OTA ZIPs, and build.prop.
* **Phase 4: Evidence-Linked Research Engine**: Normalized multi-source evidence models, deterministic evidence graph, and 6 explainable research rules.
* **Phase 5: Research Validation & Evaluation**: 35-case ground-truth corpus, categorical metrics, confusion matrices, and bit-for-bit reproducibility tracking.
* **Phase 6: Release Engineering & Open-Source Readiness**: Zero-runtime-dependency Python packaging, isolated wheel testing, end-to-end synthetic demo, security architecture, and distribution documentation.

### Core Command Groups:
* **System & Environment**: `aegis doctor`, `aegis devices`, `aegis menu`
* **Device Reconnaissance**: `aegis collect` (alias: `aegis scan`), `aegis report`, `aegis validate`
* **Evidence Snapshots & Diffs**: `aegis snapshot`, `aegis diff`
* **Firmware Intelligence**: `aegis firmware inspect`, `aegis firmware report`, `aegis firmware validate`
* **Research Engine**: `aegis research analyze`, `aegis research report`, `aegis research validate`
* **Evaluation & Reproducibility**: `aegis evaluation run`, `aegis evaluation report`, `aegis evaluation validate`
* **Demos & Verification**: `aegis demo`, `./run.sh demo-e2e` (or `bash scripts/demo.sh`)

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

## Phase Two: Evidence Snapshots & Semantic Diffs

AEGIS Phase Two enables saving immutable, versioned observation snapshots and performing deterministic, offline semantic comparisons across collection points (e.g. before and after an OEM system update, or during security baseline drift tracking).

### Core Concepts

#### 1. What is an Evidence Snapshot?
An Evidence Snapshot (`EvidenceSnapshot`, format version `0.1.0`) is a standalone, versioned JSON envelope wrapping canonical observation records and sanitized device metadata. Snapshots can be archived, transferred, and compared offline without ADB or phone connectivity.

#### 2. Canonical SHA-256 Content Hash
To ensure byte-for-byte reproducibility and tamper resistance:
* **Canonical Serialization**: JSON is serialized with deterministic key ordering (`sort_keys=True`), compact separators (`,`, `:`), and UTF-8 encoding (`ensure_ascii=False`).
* **Cryptographic Hash Input**: SHA-256 is computed over the canonical evidence payload:
  * **Included**: `source_schema_version`, provenance flag (`is_synthetic`), sanitized device identities (`serial_redacted`, `manufacturer`, `model`, `product_name`, `android_version`, `sdk_version`, `security_patch`, `build_id`, `fingerprint`), and all observation records (`key`, `status`, `value`, `raw_value`, `error`, `redacted`). Observations are deterministically sorted by `key`.
  * **Excluded**: Ephemeral envelope metadata (e.g. `created_at_utc`, collection host OS/Python/ADB versions, file paths, user notes). This guarantees that the exact same observed device state receives the identical content hash regardless of when or where the snapshot file was generated.
* **Integrity Verification**: When loading any snapshot, AEGIS recomputes the content hash and verifies it against the recorded `content_hash`. Tampered, corrupted, or altered files are rejected with a clear `SnapshotIntegrityError`.

#### 3. Pure Semantic Diff Engine
The diff engine (`compare_snapshots`) operates offline without ADB or network access:
* **Observation Classifications**:
  * `unchanged`: Observation key exists in both snapshots with identical status and value.
  * `value_changed`: Same key and comparable statuses, but observed property value changed.
  * `status_changed`: Observation status changed (e.g. `observed` -> `inaccessible` or `unsupported` -> `observed`).
  * `added`: Observation exists only in current snapshot.
  * `removed`: Observation exists only in baseline snapshot.
  * `incomparable`: Semantic comparison cannot be interpreted reliably.
* **Status Vocabulary**: Handles `observed`, `unsupported`, `inaccessible`, `not_applicable`, `unknown`, and `error` transitions faithfully without inventing security interpretations.
* **Device Comparability Safeguards**:
  * Different physical devices or conflicting models/serials are blocked by default (`IncomparableDeviceError`) to prevent misattributing differences between two distinct handsets as state changes.
  * Synthetic fixture data is strictly distinguished from live physical handset evidence; synthetic vs physical comparisons are rejected by default.
  * Missing identity information is classified as `identity_unverified` rather than assumed to match.
  * A research override (`--allow-different-devices`) is provided for cross-OEM analysis, prominently marked with warning banners in terminal and HTML reports.

#### 4. Limitation & Integrity Notice
A content hash detects changes relative to the hashed representation; it does **not** establish that the source evidence was truthful or that the snapshot was signed by a trusted authority. AEGIS reads userspace properties exposed over ADB and does **not** provide hardware-backed attestation or bootloader cryptographic validation.

---

### Phase 2 Workflow Example (Offline Synthetic Smoke Test)

```bash
# 1. Create baseline snapshot from sample evidence
./run.sh snapshot tests/fixtures/sample_evidence.json --out snapshots/baseline.json

# 2. Create updated snapshot from post-update evidence
./run.sh snapshot tests/fixtures/sample_evidence_updated.json --out snapshots/updated.json

# 3. Perform semantic diff in terminal
./run.sh diff snapshots/baseline.json snapshots/updated.json

# 4. Export machine-readable JSON diff
./run.sh diff snapshots/baseline.json snapshots/updated.json --format json --out reports/diff.json

# 5. Generate self-contained HTML visual comparison report
./run.sh diff snapshots/baseline.json snapshots/updated.json --format html --out reports/diff.html
```

---

---

## Phase Three: Offline Firmware Intelligence Engine

AEGIS Phase Three adds safe, offline, read-only static inspection of user-supplied Android firmware artifacts and partition images. It extracts header metadata, verifies container integrity, catalogues partition components, and generates deterministic, provenance-rich reports in terminal, JSON, and self-contained HTML formats.

### Mission & Safety Boundaries

AEGIS is strictly a reconnaissance and inspection toolkit. The firmware engine:
* **Never flashes firmware or modifies device state**: All analysis is local and read-only.
* **Never executes firmware binaries**: ELF executables, shell scripts, recovery installers, and partition binaries are never run.
* **Never downloads or scrapes firmware**: AEGIS inspects only explicitly provided local files or directories.
* **Does not claim OEM authenticity from hashes**: File SHA-256 hashes verify file integrity, not vendor cryptographic signatures or hardware trust.
* **Distinguishes format detection from parser results**: Recognizing magic bytes does not imply successful structural parsing or format compliance.
* **Does not conflate firmware metadata with live device state**: Firmware findings are held in distinct schemas (`FirmwareReport`, format `0.1.0`) and are never labeled as live physical device observations.

---

### Supported Formats & Capabilities

| Format | Magic / Signature | Supported Scope | Exact Capabilities & Limitations |
| :--- | :--- | :--- | :--- |
| **Android Boot Image** | `ANDROID!` | Headers v0, v1, v2, v3, v4 | Extracts page size, kernel/ramdisk/second/recovery_dtbo/dtb sizes, kernel cmdline, and decodes AOSP `os_version` and `os_patch_level` bitfields. Validates declared offsets against actual file size. Does not extract compressed ramdisk payloads. |
| **Vendor Boot Image** | `VNDRBOOT` | Headers v3, v4 | Extracts vendor ramdisk size, bootconfig size, page size, dtb size, vendor ramdisk table size, and cmdline. |
| **Android Sparse Image** | `0xED26FF3A` | Major version 1 | Validates 28-byte sparse header, declared chunk count, block size, and sequentially validates chunk descriptors (`RAW`, `FILL`, `DONT_CARE`, `CRC32`). Verifies chunk boundaries without decompressing or expanding partitions to disk. |
| **ZIP / OTA Archive** | `PK\x03\x04` | Standard ZIP32/ZIP64 | Inspects directory listings without uncompressing files. Enforces entry limits (max 50,000 entries), records total uncompressed size, detects duplicate names, and flags path traversal (`../`, absolute paths). Identifies Android components (`payload.bin`, `boot.img`, `super.img`, `vbmeta.img`) and boundedly extracts `META-INF/com/android/metadata`. |
| **Android Build Properties** | `*.prop` text | Standard properties | Parses key-value pairs (e.g. `ro.product.model`, `ro.build.version.release`) with a 4KB per-line safety limit and maximum 256KB total size. |

---

### Resource Limits & Untrusted Input Safeguards

* **Streaming SHA-256**: Hashes are computed via chunked 64KB reads, preventing high memory usage on large image files.
* **Symlink Directory Escape Guard**: Recursive directory scans resolve absolute paths and reject symlinks pointing outside the target directory.
* **Configurable File Size Ceilings**: Files exceeding `--max-size-mb` (default 2048 MB) are skipped with an `inaccessible` status.
* **ZIP Bomb & Traversal Protection**: Archive inspection limits entry counts, tallies uncompressed bytes, and alerts on path traversal attempts.
* **Zero Network Activity**: Operates completely offline with zero telemetry or remote calls.

---

### CLI Workflows & Examples

#### 1. Inspect Firmware (Single Image or Directory)
```bash
# Terminal summary output
./run.sh firmware inspect /path/to/boot.img

# Structured JSON report output
./run.sh firmware inspect /path/to/firmware_dir/ --format json --out firmware_reports/report.json

# Interactive, self-contained HTML report
./run.sh firmware inspect /path/to/ota_update.zip --format html --out firmware_reports/report.html
```

#### 2. Validate Firmware Report Integrity
```bash
# Validate schema version, summary counts, and required fields
./run.sh firmware validate firmware_reports/report.json
```

#### 3. Render HTML Report from Existing JSON
```bash
# Generate self-contained HTML from a previously generated JSON report
./run.sh firmware report firmware_reports/report.json --format html --out firmware_reports/report.html
```

#### 4. Interactive Menu
Launch the interactive developer menu and select option `7) Inspect firmware artifact or directory`:
```bash
./run.sh
```

---

---

## Phase Four: Evidence-Linked Boot-Chain Research Engine

AEGIS Phase Four adds a deterministic, offline, explainable research engine that correlates evidence from live device reconnaissance (Phase 1), evidence snapshots and semantic diffs (Phase 2), and offline firmware intelligence (Phase 3).

### Mission & Explainability Principles

AEGIS is an open research and reconnaissance toolkit, not a black-box security scanner:
* **Traceability**: Every derived research claim links directly back to the exact supporting and contradicting raw evidence IDs that produced it.
* **Prerequisite Accounting**: Every rule evaluation records exactly which prerequisites were checked, which were satisfied, and which were missing.
* **Conflict Preservation**: When two sources disagree (e.g. build release or model mismatches between live telemetry and firmware), AEGIS preserves both values and records an active conflict rather than arbitrarily favoring one source.
* **Transparent Uncertainty**: The engine explicitly catalogues what *cannot* be concluded due to missing or inaccessible observation surfaces.
* **No False Precision**: Avoids arbitrary percentages or probabilistic security scores. Uses defensible, documented certainty classifications.
* **Explicit Non-Goal**: Never outputs a binary "secure" or "compromised" verdict based on userspace properties or static images alone.

---

### Certainty Classifications

| Certainty Level | Criteria & Meaning |
| :--- | :--- |
| **`directly_observed`** | Direct, authoritative point measurement present with `observed` status in source evidence. |
| **`strongly_supported`** | All required rule prerequisites are satisfied, and conclusions are corroborated without contradiction. |
| **`tentatively_supported`** | Supported by single-source findings or partial indicators with documented assumptions. |
| **`insufficient_evidence`** | Critical prerequisites are missing or properties are `inaccessible`/`unsupported`, preventing conclusive analysis. |
| **`conflicting_evidence`** | Active contradictions or divergent values detected across two or more compared sources. |

---

### Core Research Rule Registry

* **`RULE-BOOT-CHAIN-COMPLETE`**: Evaluates completeness of core Android bootloader and verified-boot properties (`ro.boot.verifiedbootstate`, `ro.boot.flash.locked`, `ro.bootloader`, etc.).
* **`RULE-DIFF-BOOT-DRIFT`**: Evaluates semantic diffs to detect boot-chain or build property state transitions across snapshot collection points.
* **`RULE-FW-BOOT-VALID`**: Validates structural integrity and AOSP header version compliance (v0 through v4) in firmware boot and vendor_boot artifacts.
* **`RULE-CROSS-SOURCE-CONSISTENCY`**: Correlates comparable build IDs, OS versions, and model strings between live device telemetry and firmware container metadata.
* **`RULE-PROVENANCE-BOUNDARY`**: Flags comparisons crossing synthetic mock data and physical handset boundaries without explicit research overrides.
* **`RULE-INACCESSIBLE-EVIDENCE-LIMIT`**: Identifies properties blocked by OS permissions or SELinux policies, documenting the exact perimeter of the observation surface.

---

### Evidence Graph Topology

The research engine compiles a deterministic, serializable graph with strict referential integrity (zero dangling edges):
* **Node Types**: `device`, `observation`, `firmware_artifact`, `firmware_component`, `snapshot`, `diff`, `claim`, `rule_evaluation`.
* **Relationship Types**: `observed_on`, `contained_in`, `derived_from`, `compared_with`, `supports`, `contradicts`, `requires`, `related_to`.

---

### CLI Workflows & Examples

#### 1. Analyze & Correlate Evidence Sources
```bash
# Terminal summary output across multiple reports or directories
./run.sh research analyze /path/to/evidence.json /path/to/firmware_report.json

# Structured JSON research report
./run.sh research analyze /path/to/reports/ --format json --out research_reports/research.json

# Interactive, self-contained HTML report with graph overview
./run.sh research analyze /path/to/reports/ --format html --out research_reports/research.html
```

#### 2. Validate Research Report Schema & Graph Integrity
```bash
# Validate schema version, summary counts, and graph referential integrity
./run.sh research validate research_reports/research.json
```

#### 3. Render HTML Report from Existing JSON
```bash
# Generate self-contained HTML report from previously saved research JSON
./run.sh research report research_reports/research.json --format html --out research_reports/research.html
```

#### 4. Interactive Developer Menu
Launch the interactive menu and select option `8) Research engine`:
```bash
./run.sh
```

---

## Phase Five: Research Validation, Evaluation & Reproducibility

Phase Five introduces a disciplined, offline evaluation framework to establish the quality, reliability, reproducibility, and boundaries of AEGIS capabilities.

### Evaluation Corpus Overview (35 Cases)
* **Category A: Normalization & Schema (7 cases)**: Phase 1 device reports, Phase 2 snapshots & semantic diffs, Phase 3 firmware reports, missing required fields, unsupported schema versions, and malformed JSON syntax.
* **Category B: Graph Integrity (5 cases)**: Multi-source graph topologies, dangling edge rejection, duplicate node detection, invalid edge relationships, and canonical deterministic sorting.
* **Category C: Rule Evaluation (13 cases)**: Positive, negative, boundary, and inapplicable test cases across all 6 research rules (`RULE-BOOT-CHAIN-COMPLETE`, `RULE-DIFF-BOOT-DRIFT`, `RULE-FW-BOOT-VALID`, `RULE-CROSS-SOURCE-CONSISTENCY`, `RULE-PROVENANCE-BOUNDARY`, `RULE-INACCESSIBLE-EVIDENCE-LIMIT`).
* **Category D: Cross-Source Correlation (3 cases)**: Build and model conflicts, partial correlation with missing baseline inventory, and duplicate artifact deduplication.
* **Category E: Security & Robustness (4 cases)**: HTML/script injection escaping, symlink escape prevention, oversized input bounds, and zero network activity.
* **Category F: Reproducibility & Regression (3 cases)**: Byte-for-byte report and hash stability across repeated runs, argument ordering independence, and real physical handset observation telemetry.

For a detailed explanation of the methodology and non-goals, see [AEGIS Evaluation Methodology](docs/evaluation-methodology.md).

### Evaluation CLI Usage

#### 1. Run Evaluation Suite Against Default Corpus
```bash
# Run complete evaluation suite and print terminal summary
./run.sh evaluation run

# Run evaluation suite and output self-contained HTML report
./run.sh evaluation run --format html --out evaluation_reports/report.html
```

#### 2. Validate Evaluation Report Schema
```bash
# Validate evaluation report structure and metric count reconciliation
./run.sh evaluation validate evaluation_reports/evaluation-20261022-070201.json
```

#### 3. Render HTML Report from Existing Evaluation JSON
```bash
./run.sh evaluation report evaluation_reports/evaluation-20261022-070201.json --format html --out evaluation_reports/report.html
```

---

## Development, Testing & Reproducibility

### 1. Run Complete Automated Test Suite (184 Tests)
```bash
# Run pytest across all test modules
python3 -m pytest -v

# Run Ruff linter
python3 -m ruff check .
```

All 184 tests execute against synthetic fixtures, programmatically generated binary buffers, and mock environments without requiring a physical handset, live ADB connection, or proprietary vendor firmware.

### 2. Run Offline End-to-End Synthetic Demo
```bash
# Exercise snapshots, diffs, research graph, and evaluation runner in an isolated temp directory
./run.sh demo-e2e
# Or: bash scripts/demo.sh
```

### 3. Build & Test Package Distribution Artifacts
```bash
# Build source distribution and wheel
python3 -m build

# Test installation in clean isolated environment
python3 -m venv /tmp/aegis_clean_test
/tmp/aegis_clean_test/bin/pip install dist/*.whl
/tmp/aegis_clean_test/bin/aegis --help
/tmp/aegis_clean_test/bin/aegis doctor
rm -rf /tmp/aegis_clean_test
```

---

## Documentation Index

* **[Installation Guide](docs/installation.md)**: Prerequisites, clean installation, platform tools setup, and troubleshooting.
* **[Architecture Document](docs/architecture.md)**: Architectural design, dataflow diagrams, and subsystem breakdown across all 6 phases.
* **[Security & Privacy Architecture](docs/security-and-privacy.md)**: Threat model, read-only guarantees, consent gating, identifier redaction, and safe input handling.
* **[Evaluation Methodology](docs/evaluation-methodology.md)**: Scientific validation approach, metric formulations, ground-truth corpus, and threats to validity.
* **[Release Engineering Guide](docs/releasing.md)**: Release checklist, versioning policy, artifact verification, and tagging procedure.
* **[Evidence Schema Specification](docs/evidence-schema.md)**: JSON data dictionary, schema versioning, and controlled status vocabulary.
* **[Device Support Matrix](docs/device-support.md)**: Tested handsets, platform tiers, and boundary conditions.
* **[Changelog](CHANGELOG.md)**: Full milestone and release history across Phases 1 through 6.

---

## License

MIT License. See [LICENSE](LICENSE).

