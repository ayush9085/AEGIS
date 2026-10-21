# Device support policy

## Initial research target

Samsung Galaxy M11 — exact model identifier, region/CSC, firmware build, Android version, and patch level are **not yet verified**. Record these from the owner's device and authoritative sources before claiming support for a particular build.

## Support tiers

- **Tier 0 — Documentation only:** public platform/vendor documentation; no connected device needed.
- **Tier 1 — Discovery:** ADB executable detection and adb devices listing (implemented).
- **Tier 2 — Read-only inventory:** proposed opt-in collection of a reviewed, allowlisted set of device properties.
- **Tier 3 — Firmware artifact analysis:** proposed offline parsing of user-provided firmware files, with hashes and provenance.
- **Not in scope:** unlocking, flashing, rooting, bypassing verified boot, extracting private user data, or exploiting devices.

## Evidence requirements

A device/build support claim should include exact model and build identifiers, collection method, date, tool version, source references, limitations, and a reproducible test where possible. Do not generalize from one build to every device in the product family.
