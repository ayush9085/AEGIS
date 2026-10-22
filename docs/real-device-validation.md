# AEGIS Milestone 1.5: Real Device Validation & Evidence Accuracy Audit Report

**Date of Execution:** 2026-10-22  
**Milestone Status:** **PASS** (Physical device detected, authorized, collected, and audited with 100% parity)  
**Host Environment:** MacBook Air M4 (macOS Darwin 27.0.0, Apple Silicon `arm64`)  
**Python Runtime:** Python 3.12.0  
**Android Platform Tools (ADB):** Android Debug Bridge version 1.0.41 (Platform Tools 37.0.1, `/opt/homebrew/bin/adb`)  
**Target Handset:** Xiaomi Redmi Note 13 5G (Model: `2312DRAABI`, Codename: `gold`)  
**Android Version:** Android 15 (SDK 35, Build ID: `AP3A.240905.015.A2`)  

---

## 1. Executive Summary & Milestone Status

* **Status:** `PASS`
* **Target Handset Discovered:** Physical device attached over USB, identified as `Xiaomi 2312DRAABI` (Redmi Note 13 5G, codename `gold`).
* **Workflow Executed:**
  1. `aegis doctor`: Environment preflight PASSED with official ADB v37.0.1.
  2. `aegis devices`: Detected attached handset in authorized `device` state (Serial: `on***wk`).
  3. `aegis collect`: Executed 15 read-only allowlist probes with explicit consent.
  4. `aegis validate`: Validated generated evidence against JSON Schema v0.1.0 (15 observations).
  5. `aegis report`: Rendered self-contained HTML report with real-device provenance banner and masked identifiers.
  6. **Independent Evidence Accuracy Audit**: Fresh manual queries were run directly against the device and compared against collected evidence — **15 of 15 probes verified as exact MATCH (100% accuracy)**.

---

## 2. Environment Preflight & Device Discovery

```bash
./run.sh doctor
./run.sh devices
```

### Measured Host Output:
```text
AEGIS Version: 0.1.0
Host Platform: Darwin 27.0.0 (arm64)
Python: 3.12.0 (/Library/Frameworks/Python.framework/Versions/3.12/bin/python3)
ADB Binary: /opt/homebrew/bin/adb
ADB Version: Android Debug Bridge version 1.0.41
Status: Environment ready for read-only ADB research.

SERIAL		STATE
--------------------------------
on***wk		device
```

---

## 3. Independent Evidence Accuracy Audit Table (Phase F)

Fresh, independent read-only ADB commands were executed against the device and compared value-for-value against the collected JSON bundle:

| Probe / Property | Collected Value (`evidence.json`) | Fresh Independent Query (`adb shell`) | Audit Result | Technical Notes |
| :--- | :--- | :--- | :--- | :--- |
| `product.manufacturer` | `Xiaomi` | `getprop ro.product.manufacturer` -> `Xiaomi` | **MATCH** | Hardware manufacturer brand |
| `product.model` | `2312DRAABI` | `getprop ro.product.model` -> `2312DRAABI` | **MATCH** | Market model (Redmi Note 13 5G) |
| `product.name` | `gold_in_global` | `getprop ro.product.name` -> `gold_in_global` | **MATCH** | Regional firmware branch (India/Global) |
| `product.device` | `gold` | `getprop ro.product.device` -> `gold` | **MATCH** | Hardware platform board codename |
| `build.version.release` | `15` | `getprop ro.build.version.release` -> `15` | **MATCH** | User-visible Android release |
| `build.version.sdk` | `35` | `getprop ro.build.version.sdk` -> `35` | **MATCH** | Android Framework API Level 35 |
| `build.version.security_patch` | `2026-06-01` | `getprop ro.build.version.security_patch` -> `2026-06-01` | **MATCH** | Declared vendor patch level |
| `build.id` | `AP3A.240905.015.A2` | `getprop ro.build.id` -> `AP3A.240905.015.A2` | **MATCH** | System build ID |
| `build.fingerprint` | `Redmi/gold_in_global/gold:15/AP3A.240905.015.A2/OS3.0.3.0.VNQINXM:user/release-keys` | `getprop ro.build.fingerprint` -> `Redmi/...` | **MATCH** | Full system build fingerprint |
| `bootloader.version` | `unknown` | `getprop ro.bootloader` -> `unknown` | **MATCH** | Xiaomi bootloader omits `ro.bootloader` in userspace |
| `kernel.version` | `6.6.89-android15-8-gbe8d201b0d27-ab13762941-4k` | `uname -r` -> `6.6.89-...` | **MATCH** | Linux 6.6 GKI (Generic Kernel Image) kernel |
| `boot.verifiedbootstate` | `green` | `getprop ro.boot.verifiedbootstate` -> `green` | **MATCH** | AVB verified boot state passed to kernel |
| `boot.vbmeta_state` | `locked` | `getprop ro.boot.vbmeta.device_state` -> `locked` | **MATCH** | AVB 2.0 metadata locked state |
| `boot.flash_locked` | `1` | `getprop ro.boot.flash.locked` -> `1` | **MATCH** | Bootloader flash lock flag (1 = locked) |
| `boot.veritymode` | `enforcing` | `getprop ro.boot.veritymode` -> `enforcing` | **MATCH** | dm-verity active enforcement mode |

* **Total Probes Attempted**: 15  
* **Exact Matches**: 15 (100% agreement)  
* **Mismatches**: 0  

---

## 4. Report & Provenance Verification

* **Real Device HTML Report**: Saved locally at `reports/real-device-20261022/report.html` (gitignored for privacy).
* **Provenance**:
  * Real device report displays blue notice: `Real Device ADB Collection: Recorded from active Android handset at 2026-10-22T02:53:59Z`.
  * Demo report displays prominent yellow warning: `⚠️ SYNTHETIC DEMO DATA — NOT COLLECTED FROM A PHYSICAL DEVICE`.
* **Privacy Controls**: Target serial masked to `on***wk`; no personal data, app accounts, contacts, or photos collected.
* **Security Caveats**: Clearly states that reported boot properties represent userspace observations and do not independently certify hardware root of trust.

---

## 5. Quality Assurance

* **Pytest**: 60 unit tests passed (100% pass rate).
* **Ruff Linter**: Clean (0 warnings, 0 errors).
