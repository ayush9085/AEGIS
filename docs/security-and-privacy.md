# AEGIS Security, Privacy & Safety Architecture

**Version:** `0.1.0`  
**Status:** Public Release Safety Architecture  
**Scope:** Device observation, evidence snapshots, firmware intelligence, research correlation, evaluation suite.

---

## 1. Guiding Safety Philosophy

AEGIS is built on the principle that **security reconnaissance must never destabilize or endanger the system being inspected**.

```
             ┌─────────────────────────────────────────────────────────┐
             │               AEGIS Host Workstation                    │
             │   (Read-Only by Default • Local-First • Zero Cloud)      │
             └──────────────────────────┬──────────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────────┐
             │                  Guarded Interfaces                     │
             │  • ADB Allowlist (15 unprivileged read-only queries)   │
             │  • Static File Parsers (bounds-checked binary reads)   │
             │  • Local Storage (untracked, gitignored evidence)       │
             └──────────────────────────┬──────────────────────────────┘
                                        │
         ┌──────────────────────────────┴──────────────────────────────┐
         ▼                                                             ▼
┌──────────────────┐                                         ┌──────────────────┐
│  Android Handset │                                         │ Static Firmware  │
│  (Zero Flashing, │                                         │ (Zero Execution, │
│   Zero Root,     │                                         │  Zero Scraping,  │
│   Zero Mod)      │                                         │  Zero Flashing)  │
└──────────────────┘                                         └──────────────────┘
```

---

## 2. Hardware Safety & Read-Only Guarantees

### A. Bootloader Integrity
> [!CAUTION]
> **AEGIS NEVER REQUIRES BOOTLOADER UNLOCKING.**  
> Unlocking an Android bootloader wipes user partitions, permanently trips tamper indicators (such as the Samsung Knox warranty bit `0x1`), disables hardware-backed keystores, and invalidates Verified Boot protections. AEGIS operates entirely within the constraints of locked, production retail devices.

### B. Command Allowlist
Live device interrogation is restricted to a hardcoded, unprivileged allowlist defined in `src/aegis/collectors/allowlist.py`:
* **Permitted Command Families**: Only `getprop <prop_name>` and `uname -r`.
* **Prohibited Commands**: All write operations, partition reads (`dd`, `cat /dev/block/*`), package installation (`pm install`), bootloader triggers (`reboot bootloader`, `fastboot`), logcat dumping, and process memory extraction are strictly excluded from the execution engine.
* **No Privilege Escalation**: AEGIS does not invoke `su`, root binaries, or exploit payloads. If a property requires root privileges, AEGIS records its status as `inaccessible` rather than attempting privilege escalation.

### C. Explicit Informed Consent
Before a single command is dispatched to an attached handset, AEGIS presents the complete collection plan to the user in the terminal, detailing:
1. Target device serial and state.
2. Number of planned queries (15 allowlisted probes).
3. Exact command strings to be executed.
4. Scope boundary and local output location.

Execution proceeds only upon typing `yes` (or providing the automated CI flag `--yes`).

---

## 3. Privacy & Sensitive Data Handling

### A. Zero Telemetry & Offline Operation
AEGIS makes **zero network calls** during analysis. The entire toolchain (data collection, hashing, diffing, firmware parsing, rule evaluation, and HTML report rendering) operates locally and offline without remote servers, tracking beacons, analytics, or telemetry.

### B. Hardware Identifier Redaction
To protect user privacy when sharing or archiving reports:
* **Serial Numbers**: Handset serial numbers are automatically redacted by replacing middle characters with asterisks (e.g. `SM*****01`).
* **Telephony & Network Identifiers**: IMEIs, IMSIs, phone numbers, and MAC addresses are explicitly omitted from collection plans. In addition, an active regex filter (`src/aegis/redaction.py`) sanitizes output text.
* **Personal Data Safeguards**: Account databases, SMS/MMS messages, contact lists, photos, files in `/sdcard`, and application state are never accessed.

### C. Local Repository Hygiene
All live device evidence documents, snapshot files, firmware reports, and HTML artifacts are automatically excluded from version control via `.gitignore`:
```gitignore
/evidence/
/reports/
/snapshots/
/firmware_reports/
/research_reports/
/evaluation_reports/
*.device-dump
*.adb-log
```
Only synthetic fixtures (clearly stamped with `"is_synthetic": true`) are stored in the repository for regression testing and evaluation.

---

## 4. Untrusted Input & Parser Defenses

When inspecting firmware archives, images, or imported evidence files:

### A. Path Traversal & Symlink Escapes
* **Directory Scans**: Recursive directory inspection in the firmware and research engines resolves real target paths. Symlinks pointing outside the target directory are detected and rejected.
* **ZIP Archive Protection**: ZIP directory listings are inspected without uncompressing payloads. Any entry containing relative path traversal (`../`) or absolute path prefixes (`/`) is flagged and prevented from escaping.

### B. Resource Boundaries & DoS Prevention
* **Streaming Hash Calculation**: SHA-256 hashes are computed in 64 KB chunks to prevent loading gigabyte-sized partition images entirely into RAM.
* **File Size Caps**: Files exceeding `--max-size-mb` (default: 2,048 MB) are skipped safely.
* **Line Length Limits**: Text parsers (such as `build.prop` readers) enforce strict limits (4 KB per line, 256 KB total file size) to prevent memory exhaustion from crafted inputs.
* **ZIP Bomb Mitigations**: ZIP archive parsers enforce an entry cap (50,000 entries) and monitor declared uncompressed sizes before proceeding.
* **Sparse Image Chunk Verification**: Android sparse headers and chunk descriptors are verified sequentially; raw chunks are never uncompressed into memory or expanded to disk.

### C. HTML Report Escaping (XSS Prevention)
All generated HTML reports (single-collection reports, semantic diff reports, firmware reports, research graph reports, and evaluation reports) adhere to strict security policies:
* **Strict Escaping**: Every dynamic value, error message, property string, and commit metadata field is sanitized using `html.escape(..., quote=True)`.
* **Zero External Dependencies**: Reports embed 100% of their styles inline. Zero external stylesheets, remote fonts, or CDN-hosted scripts (`https://`, `http://`) are included.
* **Zero Script Execution**: Reports are rendered as pure, static HTML/CSS documents without interactive JavaScript execution.

---

## 5. Non-Goals & Scientific Boundaries

AEGIS is an empirical reconnaissance and research toolkit. It explicitly does **not** provide:
1. **Hardware-Backed Attestation**: Reading userspace build properties or bootloader strings over ADB does not verify cryptographic signatures or attest hardware authenticity.
2. **Malware or Rootkit Certification**: Passing AEGIS checks or observing standard properties does not certify that an Android kernel, firmware, or system image is uncompromised or free of stealth rootkits.
3. **Exploit Capabilities**: AEGIS is purely defensive and investigative; it does not contain exploit tools, rooting exploits, or bypasses.

---

## 6. Vulnerability Reporting

If you identify a security vulnerability, path traversal bypass, or unintended execution vector in AEGIS:
* Please do **not** open a public issue with sensitive exploit details.
* Report your findings directly to the repository maintainers via GitHub Private Vulnerability Reporting or via email as designated in the repository profile.
* Disclosures will be acknowledged within 48 hours and investigated promptly.
