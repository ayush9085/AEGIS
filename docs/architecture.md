# Architecture

## Phase One Architecture

AEGIS (*Android Exploration, Ground-Truth Inspection & Security*) decouples device transport, property probing, normalization, schema validation, and presentation.

```text
                  +-------------------------+
                  |     CLI Entrypoint      |
                  |     (aegis.cli)         |
                  +------------+------------+
                               |
       +-----------------------+-----------------------+
       |                       |                       |
       v                       v                       v
+--------------+      +------------------+     +----------------+
|  Environment |      |    Collectors    |     | Report Render  |
|   & Device   |      |  (Allowlist &    |     |  (Self-reliant |
|  Discovery   |      |   Engine)        |     |   HTML + CSS)  |
|  (aegis.adb) |      +--------+---------+     +----------------+
+--------------+               |
                               v
                      +------------------+
                      |  Evidence Schema |
                      |  & Normalization |
                      |  (aegis.schema)  |
                      +--------+---------+
                               |
                               v
                      +------------------+
                      | Privacy & Serial |
                      |    Redaction     |
                      | (aegis.redaction)|
                      +------------------+
```

## Subsystems

### 1. Transport & Discovery (`aegis.adb`)
- Wraps host `adb` binary interactions with `subprocess.run(shell=False)`.
- Never invokes a shell interpreter for arguments.
- Enforces strict execution timeouts (`DEFAULT_ADB_TIMEOUT_SECONDS = 10.0`) and maximum output boundaries (64KB buffer truncation) to eliminate hang risks and memory exhaustion.
- Enforces explicit connection state discovery: distinguishes `device`, `unauthorized`, and `offline` endpoints.

### 2. Collection Engine (`aegis.collectors`)
- Probing is governed by `ALLOWLIST_ITEMS` in `aegis.collectors.allowlist`.
- Prior to execution, users are presented with a collection plan and must confirm explicit consent (or pass `--yes`).
- Probes are strictly read-only (`getprop` and `uname -r`).
- Captures raw outputs, standard errors, and exit codes.
- Translates outcomes into the controlled status vocabulary:
  - `observed`: successfully probed and non-empty.
  - `unsupported`: returned empty string or property nonexistent on target Android build.
  - `inaccessible`: denied by OS permissions or SELinux policy.
  - `error`: command execution error or timeout.

### 3. Evidence Schema & Validation (`aegis.schema`)
- Versioned JSON evidence schema (`CURRENT_SCHEMA_VERSION = "0.1.0"`).
- Structured dataclasses for `EvidenceReport`, `DeviceContext`, `CollectionMetadata`, `Observation`, and `SummaryCounts`.
- Schema validator (`validate_evidence_dict`) enforces structural integrity, required fields, and status vocabulary compliance.

### 4. Privacy Redaction (`aegis.redaction`)
- Scans device identifiers and masks hardware serials (retaining outer characters for tracking, e.g. `R5***67`).
- Regex scrubbers for IMEI numbers (14-16 digits) and MAC addresses.

### 5. Report Generator (`aegis.reports.html`)
- Produces self-contained, offline-compatible HTML evidence reports.
- Zero remote scripts, CDN links, external stylesheets, or fonts.
- Strictly escapes all dynamic device strings, values, and error messages via `html.escape(..., quote=True)` to prevent stored XSS attacks.
- Explicitly presents limitations, non-goals, and caveats.

---

## Phase Two Subsystems (Snapshots & Semantic Diffs)

### 6. Evidence Snapshots & Integrity (`aegis.snapshots`)
- Standalone immutable snapshot envelopes (`EvidenceSnapshot`, version `0.1.0`).
- Deterministic canonical serialization (sorted keys, compact separators, UTF-8).
- Canonical SHA-256 content hashing calculated over evidence payload excluding ephemeral envelope fields.
- Automatic content hash recomputation and tamper detection upon loading.

### 7. Pure Semantic Diff Engine (`aegis.diff`)
- Offline observation-level comparison classifying changes into `unchanged`, `value_changed`, `status_changed`, `added`, `removed`, and `incomparable`.
- Strict device comparability safeguards preventing cross-device or synthetic-vs-physical comparisons unless explicitly overridden.
- Reconciliation of summary counts and deterministic diff sorting by observation key.

---

## Phase Three Subsystems (Offline Firmware Intelligence Engine)

```text
                           +---------------------------+
                           |  Firmware CLI Commands   |
                           |  (inspect/validate/report)|
                           +-------------+-------------+
                                         |
                                         v
                           +---------------------------+
                           |  Firmware Analysis Engine |
                           |  (aegis.firmware.engine)  |
                           +-------------+-------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
+------------------+           +-------------------+           +------------------+
| Format Detector  |           | Streaming SHA-256 |           | Symlink Escape   |
| (magic sniffer)  |           | & Resource Limits |           | Guard & Traversal|
+--------+---------+           +-------------------+           +------------------+
         |
         v
+------------------+-----------------------------------------------+
|                      Format-Specific Parsers                     |
|  - Boot Image Header v0-v4 & vendor_boot v3-v4 (boot_img.py)     |
|  - Android Sparse Image Stream Validator (sparse.py)            |
|  - Safe ZIP Archive & OTA Metadata Inspector (zip_archive.py)    |
|  - Bounded Build Property Parser (props.py)                      |
+----------------------------------+-------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------+
| Versioned Firmware Report (0.1.0) & Validator (models.py)        |
+----------------------------------+-------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------+
| Self-Contained HTML Firmware Reporter (reports/firmware_html.py) |
+------------------------------------------------------------------+
```

### 8. Format Sniffing (`aegis.firmware.detector`)
- Conservative signature-based detection inspecting only leading bytes.
- Detects `android_boot_image` (`ANDROID!`), `android_vendor_boot_image` (`VNDRBOOT`), `android_sparse_image` (`0xED26FF3A`), `zip_archive` (`PK\x03\x04`), `avb_vbmeta_image` (`AVB0`), `android_payload_bin` (`CrAU`), and `android_build_prop`.
- Separates format identification from parser success; detected formats do not imply valid parsing.

### 9. Header & Container Parsers (`aegis.firmware.parsers`)
- **Boot Image Parser (`boot_img.py`)**:
  - Safely inspects header versions 0 through 4 and vendor_boot versions 3 and 4.
  - Extracts kernel, ramdisk, second stage, recovery dtbo, and dtb sizes.
  - Decodes AOSP `os_version` and `os_patch_level` bitfields into semantic releases and year-month strings.
  - Validates declared offsets and component sizes against file boundaries.
- **Sparse Image Parser (`sparse.py`)**:
  - Parses 28-byte sparse headers and validates chunk headers (`RAW`, `FILL`, `DONT_CARE`, `CRC32`).
  - Verifies block counts and file boundaries without decompressing or expanding partitions to disk.
- **ZIP / OTA Inspector (`zip_archive.py`)**:
  - Inspects archive directory records without extracting binary content.
  - Enforces entry count bounds (50,000 entries max) and total uncompressed size limits.
  - Flags duplicate entry names and directory traversal paths (`../`, absolute paths).
  - Classifies known partition images (`payload.bin`, `boot.img`, `super.img`, `vbmeta.img`) and safely extracts text properties from `META-INF/com/android/metadata`.
- **Property Parser (`props.py`)**:
  - Safely reads lines under 4KB from `build.prop` files to extract device model, manufacturer, and release details.

### 10. Firmware Analysis Engine (`aegis.firmware.engine`)
- Coordinates recursive directory scanning and single-file analysis.
- Prevents symlink traversal outside user-specified directories (`Path.resolve().is_relative_to(...)`).
- Computes SHA-256 via chunked streaming (`64KB` blocks) without loading large images into memory.
- Enforces configurable maximum file size thresholds (default `2048 MB`).

### 11. Report Schema & HTML Presentation (`aegis.firmware.models`, `aegis.reports.firmware_html`)
- Versioned `FirmwareReport` schema (`0.1.0`) with provenance-tracked `ArtifactInventory` and `FirmwareFinding` records.
- Reconciles finding counts across `observed`, `unsupported`, `inaccessible`, `not_applicable`, `unknown`, and `error`.
- Produces fully offline, self-contained HTML reports with zero CDN dependencies and strict XSS escaping on all untrusted artifact metadata.

