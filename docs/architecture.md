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
