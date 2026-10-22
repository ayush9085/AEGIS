# Device Support Policy

## Phase One Support Matrix

| Target Platform / Device | Tier | Status in Phase One | Notes |
| :--- | :--- | :--- | :--- |
| **Xiaomi Redmi Note 13 5G (`2312DRAABI`, `gold`)** | Tier 2 (Physical Device) | **Verified Live (PASS)** | Tested on hardware running Android 15 (SDK 35), Kernel 6.6 GKI. 15/15 probes audited with 100% parity. |
| **Generic Android (API 28–35)** | Tier 2 (Read-only inventory) | Supported | Standard AOSP system build and version properties queryable via allowlisted `getprop`. |
| **Samsung Galaxy M11 (`SM-M115F` / variants)** | Tier 2 (Initial Target) | Implemented & Tested via Fixtures | Handset-specific build identifiers, CSC, and security patch are discovered dynamically. |
| **Android Emulators (e.g. `emulator-5554`)** | Tier 2 (Read-only inventory) | Supported | Standard testing targets; standard serials recognized and displayed. |

## Support Tiers

- **Tier 0 — Documentation & Schema**: Public platform/vendor documentation; no connected hardware needed. Fully implemented in Phase One.
- **Tier 1 — Discovery (`aegis doctor`, `aegis devices`)**: Host ADB executable detection, version parsing, and connected device state diagnosis (`device`, `unauthorized`, `offline`). Fully implemented in Phase One.
- **Tier 2 — Read-Only Inventory (`aegis collect`, `aegis report`)**: Bounded allowlisted collection of build, kernel, and verified boot properties. Generates versioned evidence JSON and self-contained HTML. Fully implemented in Phase One.
- **Tier 3 — Firmware Artifact Analysis (Future)**: Offline parsing of official vendor firmware packages (e.g. Samsung Odin `AP`/`BL` tarballs), payload unpacking, and hash verification against public transparency logs. Planned for Phase Two/Three.

## Explicit Non-Goals & Out-of-Scope Operations

AEGIS explicitly does **NOT** support and will **NEVER** perform:
- Unlocking the bootloader (`fastboot oem unlock` or `fastboot flashing unlock`).
- Flashing partitions, boot images, recoveries, or system images.
- Elevating privileges through root (`su`), exploits, or kernel vulnerabilities.
- Reading private user data, app storage, contacts, messages, or credential stores.
- Circumventing Android Verified Boot (AVB) or OEM security checks.
