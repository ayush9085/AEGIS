# Changelog

All notable changes to AEGIS (Android Exploration, Guardrails, Intelligence & Security) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-rc1] - 2026-10-22

### Phase 6: Release Engineering & Open-Source Readiness
- **Packaging**: Standardized `pyproject.toml` with PEP 621 metadata, license declarations, classifiers, keywords, and console script entrypoints.
- **Dependency Isolation**: Verified zero runtime external dependencies (Python standard library only) and organized development dependencies (`pytest`, `ruff`, `build`).
- **End-to-End Synthetic Demo**: Added `scripts/demo.sh` and `./run.sh demo-e2e` for complete, offline, non-destructive demonstrations verifying multi-phase workflows and bit-for-bit reproducibility.
- **CLI Usability & Consistency**: Added `--overwrite` support to snapshot diffs, aligned `--out` overwrite protections across all subcommands, and expanded root parser help examples.
- **Documentation**: Added `docs/installation.md`, `docs/security-and-privacy.md`, `docs/releasing.md`, and updated `docs/architecture.md` and `README.md`.
- **Repository Hygiene**: Sanitized documentation links, updated `.gitignore` for distribution artifacts, and audited repository against accidental secret or device dump tracking.

### Phase 5: Research Validation, Evaluation & Reproducibility
- **Evaluation Subsystem**: Introduced `src/aegis/evaluation/` with versioned `EvaluationReport` (`0.1.0`) and `EvaluationManifest` (`0.1.0`).
- **Ground-Truth Corpus**: Created 35 curated cases across 6 categories (Normalization, Graph Integrity, Rule Evaluation, Cross-Source Correlation, Security & Robustness, Reproducibility).
- **Categorical & Binary Metrics**: Implemented confusion matrices (Precision, Recall, F1) strictly for binary ground-truth labels and agreement rates for multi-state rules.
- **Evaluation CLI**: Added `aegis evaluation run`, `aegis evaluation validate`, and `aegis evaluation report` (terminal, JSON, standalone HTML).
- **Evaluation Methodology**: Documented empirical boundaries, metric formulations, and scientific threats to validity in `docs/evaluation-methodology.md`.

### Phase 4: Evidence-Linked Boot-Chain Research Engine
- **Normalized Evidence Model**: Built `src/aegis/research/normalize.py` unifying Phase 1, Phase 2, and Phase 3 data structures.
- **Evidence Graph**: Implemented `EvidenceGraph` with deterministic sorting and referential integrity enforcement.
- **Deterministic Research Rules**: Created 6 explainable rules (`RULE-BOOT-CHAIN-COMPLETE`, `RULE-DIFF-BOOT-DRIFT`, `RULE-FW-BOOT-VALID`, `RULE-CROSS-SOURCE-CONSISTENCY`, `RULE-PROVENANCE-BOUNDARY`, `RULE-INACCESSIBLE-EVIDENCE-LIMIT`).
- **Research Reporting**: Introduced terminal research summaries and self-contained HTML graph visualizers.

### Phase 3: Offline Firmware Intelligence Engine
- **Static Firmware Parsers**: Implemented safe, bounds-checked parsers for Android Boot Image (v0–v4), Vendor Boot Image (v3–v4), Android Sparse Image (v1), ZIP / OTA archives, and Android `build.prop` files.
- **Resource Safeguards**: Added streaming SHA-256 chunking, directory symlink escape guards, file size limits, and ZIP traversal mitigations.
- **Firmware CLI**: Added `aegis firmware inspect`, `aegis firmware validate`, and `aegis firmware report`.

### Phase 2: Evidence Snapshots & Semantic Diffs
- **Evidence Snapshots**: Created versioned `EvidenceSnapshot` envelope with canonical SHA-256 content hashing.
- **Semantic Diff Engine**: Implemented deterministic `compare_snapshots` identifying changed, added, removed, and incomparable observations.
- **Diff Reporting**: Added terminal summaries and standalone HTML comparison reports.

### Phase 1: Read-Only Android Reconnaissance MVP
- **Safe Discovery**: Implemented `aegis devices` and `aegis doctor` for platform and ADB prerequisites.
- **Bounded Probing**: Created 15-property unprivileged allowlist for Android boot-chain inspection.
- **Consent Gating**: Mandatory user confirmation showing planned commands before live handset interrogation.
- **Data Protection**: Automated serial number redaction and sensitive identifier scrubbing.
- **Reporting**: Standalone accessible HTML single-collection reports.
