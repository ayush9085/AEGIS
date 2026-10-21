# AEGIS — Phase One Implementation Brief for Antigravity

**Repository:** https://github.com/ayush9085/AEGIS  
**Branch:** `main` (inspect before editing; preserve existing work)  
**Target workstation:** MacBook Air M4, macOS  
**Initial validation target:** Samsung Galaxy M11; exact model/build must be discovered, never assumed  
**Runtime:** Python 3.11+  
**Task:** Implement Phase One end-to-end in the existing repository. Do not return only a plan.

## 1. Role and project definition

Act as a senior Python systems engineer. Inspect the complete repository, current code, tests, CI, and git status before editing. Preserve useful existing code. Run baseline tests/lint, implement the changes, add tests, update documentation, run checks again, and report actual outcomes. Do not claim tests or real-device checks passed unless you ran them.

AEGIS means **Android Exploration, Guardrails, Intelligence & Security**. It is an open-source, evidence-driven Android boot-chain and firmware reconnaissance toolkit that turns authorized, read-only device observations into reproducible evidence and reports. It must clearly distinguish what was observed, how it was obtained, confidence/limitations, and what remains unknown.

The current repository is a starter scaffold. Its current CLI and ADB discovery are not a completed firmware analyzer. Verify actual repository state rather than assuming every file is unchanged.

## 2. Phase One objective

Deliver a usable, cross-platform MVP that can:

1. Check the local environment and ADB installation.
2. Discover ADB-visible devices.
3. Require explicit consent and show a proposed collection plan.
4. Collect a small fixed allowlist of non-personal Android build/system properties using read-only ADB calls.
5. Normalize findings into a versioned JSON evidence schema.
6. Record provenance, timestamps, tool/device context, per-check statuses, errors, and limitations.
7. Redact sensitive identifiers by default in shareable reports.
8. Generate a readable, self-contained local HTML report from saved evidence.
9. Validate/test the schema, collectors, CLI, redaction, report generation, and error handling.
10. Document setup, commands, scope, safety, limitations, and reproducible validation.

## 3. Required CLI

Keep existing command behavior where practical. Implement and test:

```text
aegis --help
aegis --version
aegis doctor
aegis devices
aegis collect --device <serial> --out <directory>
aegis report <path-to-evidence.json> --format html [--out <file>]
```

Optionally add `aegis validate <path-to-evidence.json>` after core requirements are complete.

- `doctor`: AEGIS/Python/OS versions and ADB path/version if available, with actionable diagnostics.
- `devices`: invoke only `adb devices` for discovery; handle no devices, unauthorized/offline devices, missing ADB, malformed output, timeout, and nonzero exit.
- `collect`: explicitly select the target; never silently choose between multiple devices. Reject unauthorized/offline targets. Show the fixed collection plan before collection and require consent. Save locally to the requested directory.
- `report`: validate input evidence and render a self-contained HTML report. Escape every untrusted string and error. No remote assets or scripts.
- Use useful exit codes and concise errors. Expected errors should not produce raw tracebacks.
- A non-interactive `--yes` option is acceptable only if explicit and documented; it must not bypass device selection, allowlists, or safety checks.

## 4. Safety and fixed collection allowlist

Use argument arrays with `shell=False`, timeouts, bounded output, and explicit exit-status handling. Never accept arbitrary shell commands from users. Use an allowlist of specific documented property names, for example:

- Manufacturer
- Model/product identifiers (not unique hardware serials)
- Android release
- Build ID and fingerprint
- Security patch level
- SDK/API level
- Kernel version, only through a narrow documented read-only method
- Verified-boot-related properties only when exposed and interpreted with explicit caveats
- ADB connection state

Record the collection method for every field. Do not collect IMEI/IMSI, phone numbers, contacts, messages, photos, app databases, account content, tokens, passwords, Wi-Fi passwords, location history, personal files, broad logcat output, unrestricted shell output, partition contents, or private keys. No root, bootloader unlocking, flashing, rebooting, wiping, writes, exploits, or security-control bypasses. Do not recommend unlocking as a prerequisite. No telemetry, automatic upload, or background network calls.

### Required per-check statuses

Use a controlled vocabulary that includes:
- `observed`: successfully collected
- `unsupported`: capability/field unsupported
- `inaccessible`: approved method denied/unavailable
- `not_applicable`: does not apply
- `unknown`: no reliable conclusion
- `error`: unexpected failure

Missing properties must not be treated as proof that a security feature is absent. Never produce a single overall “secure/insecure” verdict.

## 5. Versioned evidence schema

Use Pydantic or JSON Schema as a single clear source of truth. Include at minimum:

- `schema_version`
- `tool` name and version
- `collection` UTC timestamp, method, scope, and consent/plan metadata as appropriate
- `device` non-sensitive identity/build context when available
- `observations` list
- `summary` counts by status/completeness
- `limitations` and explicit statements about what was not tested

Each observation should include a stable key, label, raw value only when safe, normalized value, status, source/method/command identifier, timestamp, reason/error when not observed, confidence/interpretation caveat, and redaction metadata as appropriate.

Do not retain secrets in raw output. Prefer individual allowlisted values instead of full command output. Include at least one synthetic fixture with no real identifiers. Validate schema versions; fail safely on unknown future versions and provide helpful errors.

## 6. HTML report requirements

Generate a self-contained accessible HTML report with no CDN, external fonts, telemetry, or network dependency. Include:
1. Report heading and generation time
2. Tool/schema versions
3. Device/build profile with sensitive identifiers redacted
4. Counts of observed/unsupported/inaccessible/unknown/error checks
5. Evidence table: field, value, status, method/source, caveat
6. Errors and skipped checks
7. Limitations/non-goals
8. Reproducibility metadata

Escape all device-provided strings and errors. Never use device output to create HTML elements, attributes, CSS, or scripts. Handle malformed input and limit output sizes. Reports stay local. Clearly label synthetic examples.

## 7. Tests

Use pytest; unit tests must not require a physical phone. Mock ADB/subprocess output deterministically. Cover:

- CLI help/version/subcommands
- `doctor` with and without ADB
- Normal, empty, malformed `adb devices` output
- Unauthorized/offline device states
- Missing ADB, timeout, and nonzero exit
- Zero/one/multiple device selection
- Consent/preview behavior
- Allowlisted commands only; no arbitrary shell interpolation
- Collection output and schema validation
- Every status category
- Serial/IMEI-like identifier redaction
- Invalid/unknown schema versions
- HTML escaping, including `<script>alert(1)</script>`
- Report generation and invalid/missing input errors
- No unintended network access or write/destructive device commands

Use synthetic fixtures and temporary directories. Test behavior rather than implementation details. Add regression tests for any bugs found.

## 8. Code quality and CI

- Support Python 3.11 and 3.12.
- Keep runtime dependencies minimal; justify new dependencies.
- Add type hints for public interfaces and useful docstrings.
- Run Ruff and pytest.
- Update GitHub Actions to install the package and run tests/lint on pushes and pull requests with read-only permissions where possible.
- Keep license and metadata consistent with the existing MIT license.
- Avoid unrelated refactors and do not add an ML model in Phase One.

## 9. Documentation

Update `README.md` with honest feature status, macOS setup, installation, quick start, official Android Platform Tools link, USB debugging/authorization instructions, commands, safety/privacy, known limitations, troubleshooting, and development/testing steps. Warn users not to unlock the bootloader.

Update `docs/architecture.md`, `docs/device-support.md`, and `docs/threat-model.md` to match the actual implementation. Add:
- `docs/evidence-schema.md`: fields, versioning, status vocabulary
- `docs/phase-one-validation.md`: exact commands run, observed results, environment, and clear distinction between mocked tests and real-device validation

Do not fabricate device observations, screenshots, results, or claims of real-device validation. Do not put real private identifiers in docs or fixtures.

## 10. Definition of Done

- [ ] Existing repository work inspected and preserved.
- [ ] All required CLI commands implemented and documented.
- [ ] ADB discovery robustly handles success and failure cases.
- [ ] Collection is opt-in, fixed-allowlist, read-only, timeout-bounded, and privacy-conscious.
- [ ] Versioned JSON evidence schema is validated.
- [ ] Per-field status, provenance, and limitations are recorded.
- [ ] Sensitive identifiers are redacted by default in shareable reports.
- [ ] HTML report is self-contained and safely escapes untrusted values.
- [ ] Tests cover success, failure, privacy, schema, and injection cases.
- [ ] Ruff passes.
- [ ] pytest passes locally; Python 3.11/3.12 CI results are checked or explicitly marked pending.
- [ ] Documentation reflects implemented behavior.
- [ ] No unsupported security verdicts or false claims.
- [ ] Final report lists changed files, actual commands/results, known gaps, and next steps.

## 11. Suggested implementation order

1. Inspect repository and run baseline tests/lint.
2. Define status vocabulary and evidence model.
3. Harden/test ADB discovery and device selection.
4. Implement consent-gated allowlisted collection.
5. Implement serialization and schema validation.
6. Implement redaction and safe HTML reporting.
7. Wire CLI and exit codes.
8. Add synthetic fixtures and comprehensive mocked tests.
9. Update documentation and CI.
10. Run checks, inspect final diff, report honestly.

## 12. Explicitly out of scope

No ML anomaly detection, automatic firmware downloads, firmware flashing, partition writes, unlocking/rooting, exploits, broad filesystem/log collection, cloud upload, telemetry, accounts, hosted dashboards, or mandatory PDF export. HTML is sufficient for Phase One. Do not claim verified firmware authenticity or comprehensive device security.

## 13. Required final response from Antigravity

Report:
1. Implemented functionality
2. Key design decisions
3. File-by-file summary
4. Exact tests/lint commands and actual results
5. Whether physical-device validation was performed
6. Known limitations or failed checks
7. Commands the owner should run on macOS
8. Recommended Phase Two tasks

**Work directly in the existing repository and complete the implementation. Do not return only a proposal.**
