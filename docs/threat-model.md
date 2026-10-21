# Threat Model & Safety Boundaries

## 1. Protected Assets

* **Device State & Data Availability**: Protecting target devices against accidental modification, corruption, bricking, or unwanted state alterations.
* **User Privacy**: Safeguarding persistent unique identifiers (serials, IMEIs, MAC addresses) and ensuring zero user data is accessed or collected.
* **Host Workstation Security**: Preventing shell injection, unconstrained resource consumption, or arbitrary code execution from malicious or malformed device outputs.
* **Evidence Integrity & Provenance**: Ensuring collected evidence is reproducible, immutable, auditable, and clearly distinguished from inference.

---

## 2. Threat Analysis & Mitigations

| Threat | Impact | Implemented Mitigation |
| :--- | :--- | :--- |
| **Accidental State Modification** | Device instability or data loss. | Read-only allowlist (`ALLOWLIST_ITEMS`). Only `getprop` and `uname -r` are invoked. Destructive tokens (`rm`, `reboot`, `flash`, `wipe`) are strictly rejected. |
| **Command Injection via Malicious Input** | Arbitrary shell command execution on host or handset. | Subprocess invocations use argument vectors (`list[str]`) with `shell=False`. No shell strings are parsed or evaluated with user or device data. |
| **Unbounded Output / Memory Exhaustion** | Denial of service / host crash from bloated command outputs. | Bounded output buffer enforcement (`MAX_OUTPUT_BYTES = 65536`) truncates excessive responses. |
| **Execution Hangs / Deadlocks** | Process starvation from hung ADB connections. | Strict subprocess timeouts (`DEFAULT_ADB_TIMEOUT_SECONDS = 10.0`) terminate stalled commands deterministically. |
| **Stored Cross-Site Scripting (XSS)** | Malicious device property executes script when viewing HTML report. | All values, errors, and metadata in `aegis.reports.html` are strictly escaped via `html.escape(..., quote=True)`. Zero remote JS/CSS or external fonts. |
| **Data Leakage in Public Reports** | Leaking sensitive hardware serials, IMEIs, or MACs. | Automated masking via `aegis.redaction` obscures hardware serial numbers (e.g. `R5***67`) and scrubs IMEI / MAC patterns from shareable reports. |
| **Overclaiming / False Sense of Security** | User mistakes superficial properties for hardware security proof. | Controlled status vocabulary (`observed`, `unsupported`, `inaccessible`, `not_applicable`, `unknown`, `error`). Explicit limitations documented on every report; **no green "Secure" certification badge**. |

---

## 3. Operational Safety Rules

1. **Bootloader integrity**: Users must never be instructed to unlock bootloaders for AEGIS research.
2. **Local-first execution**: All evidence is saved locally to user-specified directories. No telemetry, analytics, or remote network requests.
3. **Auditability**: Every recorded observation retains its exact source command, timestamp, and status.
