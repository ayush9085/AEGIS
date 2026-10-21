# Architecture

## Current implementation

1. The CLI parses the requested subcommand.
2. doctor checks local Python/platform information and whether ADB is on PATH.
3. devices invokes only adb devices to enumerate attached ADB endpoints.
4. Output is printed locally. No phone shell commands, files, logs, or partitions are read.

## Planned evidence pipeline

    Research scope and consent
              |
       Environment and discovery
              |
       Collection plan preview
              |
       Explicit approval
              |
       Allowlisted read-only collectors
              |
       Normalize and redact evidence
              |
       Provenance-backed evidence bundle
              |
       Report and local diff

Every observation should record a stable field name, value, collection method, timestamp, tool version, device/build context, and confidence/limitations. Reports must distinguish direct observations from interpretation.

## Design constraints

- Separate collectors from presentation and reporting.
- Make device interaction explicit, narrow, and auditable.
- Avoid hidden network calls and telemetry.
- Never silently broaden collection scope.
- Version saved evidence schemas.
