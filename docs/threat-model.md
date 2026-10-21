# Threat model and safety boundaries

## Assets to protect

- Device integrity and availability
- Personal data and identifiers
- Firmware artifacts and their provenance
- Researcher credentials and local environment
- Accuracy and reproducibility of conclusions

## Threats

- Accidental write or destructive device command
- Publishing serial numbers, logs, or personal information
- Mistaking a user-space observation for proof of boot-chain integrity
- Malformed firmware artifacts targeting parsers
- Supply-chain risks in dependencies and build tooling
- Unsupported claims about device security properties

## Controls

- Read-only-by-default operation and explicit collection previews
- No bootloader, partition, or firmware write features in project scope
- Local-first processing; no telemetry by default
- Redaction before sharing evidence
- Hashes and provenance for imported artifacts
- Input validation, bounded parsing, and tests for malformed inputs
- CI tests and dependency review
- Clear separation between observation, inference, and uncertainty

## Responsible use

Only use AEGIS on devices and artifacts you own or are authorized to analyze. Do not use it to access another person's data, evade device protections, or perform unauthorized testing. Report security issues privately to the relevant maintainer/vendor before public disclosure.
