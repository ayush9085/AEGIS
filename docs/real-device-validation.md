# AEGIS Real-Device Validation & Evidence Audit Report

**Date of Execution:** 2026-10-22  
**Validation Status:** **VERIFIED WITH DOCUMENTED SCOPE**  
**Host Environment:** MacBook Air M4 (macOS Darwin 27.0.0, Apple Silicon `arm64`)  
**Python Runtime:** Python 3.12.0  
**Android Platform Tools (ADB):** Android Debug Bridge version 1.0.41 (Platform Tools 37.0.1, `/opt/homebrew/bin/adb`)  
**Target Handset:** Xiaomi Redmi Note 13 5G (Model: `2312DRAABI`, Codename: `gold` / `gold_in_global`)  
**Operating System:** Android 15 / Xiaomi HyperOS (SDK 35, Build ID: `AP3A.240905.015.A2`)  
**Linux Kernel:** `6.6.89-android15-8-gbe8d201b0d27-ab13762941-4k` (Android Generic Kernel Image - GKI)  

---

## 1. Executive Summary & Purpose

During the development of AEGIS, an active physical Android handset (Xiaomi Redmi Note 13 5G) was connected via USB debugging to establish real-world hardware verification.

This document records the exact findings, methodology, and empirical boundaries established by this physical handset session:
* **Live Probing Parity**: All 15 unprivileged read-only allowlist probes were executed with explicit user consent and compared against fresh, independent manual ADB queries — resulting in **15 of 15 exact matches (100% agreement)**.
* **Non-Destructive Boundary**: No root privileges, bootloader unlocking, partition dumps, or flashing operations were performed. The handset remained locked and untouched.
* **Privacy & Reproducibility**: Physical evidence files (`reports/real-device-20261022/evidence.json`) remain local and gitignored to protect the owner's hardware identifiers. Automated regression testing and CI pipelines utilize synthetic fixtures and safely skip physical cases when private fixtures are absent.

---

## 2. Environment Preflight & Device Discovery

Prior to collection, host prerequisites and transport authorization were verified:

```bash
./run.sh doctor
./run.sh devices
```

### Measured Output:
```text
AEGIS Version: 0.1.0
Host Platform: Darwin 27.0.0 (arm64)
Python: 3.12.0 (/Library/Frameworks/Python.framework/Versions/3.12/bin/python3)
ADB Binary: /opt/homebrew/bin/adb
ADB Version: Android Debug Bridge version 1.0.41
Devices Connected: 1 authorized device ready
Status: Environment ready for read-only ADB research.

SERIAL          STATE
--------------------------------
on***wk         device  Redmi 2312DRAABI (Android 15)
```

The device serial was detected over USB, verified in the authorized `device` state (RSA host key accepted), and masked as `on***wk` in public logs and generated reports.

---

## 3. Independent Evidence Accuracy Audit (15/15 Probes)

To verify that AEGIS's collection engine faithfully captures device state without hallucination, corruption, or heuristic mutation, fresh manual ADB queries were executed directly on the terminal and compared value-for-value against the generated evidence bundle:

| Property / Probe Key | Collected Value (`evidence.json`) | Independent Reference (`adb shell`) | Parity Result | Technical Context & Meaning |
| :--- | :--- | :--- | :---: | :--- |
| `product.manufacturer` | `Xiaomi` | `getprop ro.product.manufacturer` -> `Xiaomi` | **MATCH** | Brand manufacturer identity string |
| `product.model` | `2312DRAABI` | `getprop ro.product.model` -> `2312DRAABI` | **MATCH** | Hardware model number (Redmi Note 13 5G) |
| `product.name` | `gold_in_global` | `getprop ro.product.name` -> `gold_in_global` | **MATCH** | Firmware target product branch |
| `product.device` | `gold` | `getprop ro.product.device` -> `gold` | **MATCH** | Internal SoC/board architecture codename |
| `build.version.release` | `15` | `getprop ro.build.version.release` -> `15` | **MATCH** | Nominal Android platform release version |
| `build.version.sdk` | `35` | `getprop ro.build.version.sdk` -> `35` | **MATCH** | Android Framework API Level 35 |
| `build.version.security_patch` | `2026-06-01` | `getprop ro.build.version.security_patch` -> `2026-06-01` | **MATCH** | Declared vendor security patch level |
| `build.id` | `AP3A.240905.015.A2` | `getprop ro.build.id` -> `AP3A.240905.015.A2` | **MATCH** | AOSP compilation build identifier |
| `build.fingerprint` | `Redmi/gold_in_global/gold:15/AP3A.240905.015.A2/OS3.0.3.0.VNQINXM:user/release-keys` | `getprop ro.build.fingerprint` -> `Redmi/...` | **MATCH** | Cryptographic release fingerprint for OTA |
| `bootloader.version` | `unknown` | `getprop ro.bootloader` -> `unknown` | **MATCH** | Xiaomi HyperOS does not expose a bootloader string via this property; recorded faithfully as `observed: unknown`. |
| `kernel.version` | `6.6.89-android15-8-gbe8d201b0d27-ab13762941-4k` | `uname -r` -> `6.6.89-...` | **MATCH** | Active Linux GKI kernel release string |
| `boot.verifiedbootstate` | `green` | `getprop ro.boot.verifiedbootstate` -> `green` | **MATCH** | Android Verified Boot state passed to kernel (green = locked/verified) |
| `boot.vbmeta_state` | `locked` | `getprop ro.boot.vbmeta.device_state` -> `locked` | **MATCH** | AVB 2.0 cryptographic metadata partition state |
| `boot.flash_locked` | `1` | `getprop ro.boot.flash.locked` -> `1` | **MATCH** | Bootloader flash lock flag (`1` = locked) |
| `boot.veritymode` | `enforcing` | `getprop ro.boot.veritymode` -> `enforcing` | **MATCH** | dm-verity active block verification status |

* **Total Allowlist Probes**: 15  
* **Exact Matches**: 15 (100% accuracy)  
* **Mismatches / Discrepancies**: 0  

---

## 4. Phase-by-Phase Real-Device Validation Matrix

It is scientifically critical to distinguish what was proven on live hardware from what was verified via synthetic fixtures:

| Phase | Subsystem | Live Physical Device Scope | Synthetic Fixture Scope | Validation Status | Evidence Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Device Observation | Executed on Xiaomi Redmi Note 13 5G via USB ADB | Synthetic Samsung Galaxy M11 baseline | `verified_from_artifact` | `reports/real-device-20261022/evidence.json` |
| **Phase 2** | Snapshots & Diffs | Created snapshot with canonical SHA-256 hash | Tested across synthetic state transitions and tamper checks | `verified_from_artifact` (snapshot) / `synthetic_only` (diffs) | `src/aegis/snapshots.py`, `tests/test_snapshots.py` |
| **Phase 3** | Firmware Intelligence | **Untested on live device**: No partition dumps extracted (preserves non-root boundary) | Tested on synthetic boot.img (v0, v3), vendor_boot, sparse v1, OTA zips | `synthetic_only` | `src/aegis/firmware/`, `tests/test_firmware_parsers.py` |
| **Phase 4** | Research Engine | Live Redmi evidence ingested into research graph and evaluated against 6 rules | Multi-source conflict and discrepancy vectors | `verified_from_artifact` (single source) / `synthetic_only` (conflicts) | `src/aegis/research/`, `tests/test_research_engine.py` |
| **Phase 5** | Evaluation Framework | Case `REAL-01-PHYSICAL-HANDSET-EVAL` exercises live Redmi telemetry | 34 synthetic ground-truth cases across Categories A through E | `verified_from_artifact` (case REAL-01) / `synthetic_only` (corpus A-E) | `src/aegis/evaluation/corpus.py`, `tests/test_evaluation_runner.py` |
| **Phase 6** | Release Readiness | Device discovery verified live on attached handset (`aegis devices`) | Built wheel install, E2E synthetic demo, packaging checks | `verified_from_artifact` | `pyproject.toml`, GitHub Actions Run #39740636292 |

---

## 5. Privacy Safeguards & Data Hygiene

1. **Local Storage**: Physical evidence files are saved strictly to `./reports/` and `./snapshots/`, which are gitignored by default. They are never pushed to GitHub.
2. **Serial Redaction**: The device serial `onauduyhofnb4dwk` is automatically masked to `on***wk` across all UI and terminal outputs.
3. **Excluded Surfaces**: Zero personal data (accounts, contacts, messages, photos, `/sdcard`, or application databases) was collected or requested.
4. **CI Fallback**: In clean CI environments where private device reports are absent, the evaluation runner marks physical cases as `status="skipped"` without causing build failure.

---

## 6. Scientific Limitations & Boundaries

The 15/15 physical device match proves that AEGIS correctly queries, sanitizes, and serializes unprivileged Android userspace properties. However, it explicitly does **not** establish:
* **Hardware Root of Trust**: Android userspace properties reported by `getprop` originate from the Android init property service; they do not independently verify TrustZone/TEE execution.
* **Absence of Malware / Exploits**: A locked Verified Boot status (`green`, `flash_locked: 1`) indicates the declared boot state, but does not certify the device is free from runtime exploits or post-boot tampering.
* **Firmware Parser Coverage on Commercial ROMs**: Phase 3 parsers were validated on standard AOSP structures, not full commercial 4GB vendor firmware packages.
