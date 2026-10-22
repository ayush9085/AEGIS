# AEGIS Release Engineering & Distribution Guide

**Version:** `0.1.0`  
**Standard:** Semantic Versioning 2.0.0  
**Package Name:** `aegis-android-research`

---

## 1. Release Philosophy & Governance

AEGIS follows a disciplined, conservative release engineering model:
* **No Unverified Claims**: Releases must never imply that passing synthetic tests proves live handset authenticity or freedom from malware.
* **Deterministic Distribution**: All package artifacts (`.tar.gz` sdist and `.whl` wheel) must build reliably and install cleanly across Python 3.11 and 3.12 without external runtime dependencies.
* **Maintainer Sign-Off Gate**: Releases and Git tags (`vX.Y.Z`) are **never** published automatically by automated pipelines. A human maintainer must explicitly review verification criteria before cutting or publishing a release.

---

## 2. Versioning Strategy

AEGIS adheres to Semantic Versioning (`MAJOR.MINOR.PATCH`):
* `MAJOR`: Incompatible schema changes or backward-incompatible CLI restructuring.
* `MINOR`: New subsystem capabilities, additional parser formats, or rule enhancements.
* `PATCH`: Bug fixes, security hardening, or parser boundary corrections.

### Single Source of Version Truth
Version numbers must be synchronized across:
1. `src/aegis/__init__.py` (`__version__ = "0.1.0"`)
2. `pyproject.toml` (`version = "0.1.0"`)
3. `CHANGELOG.md`

---

## 3. Pre-Release Checklist (Acceptance Criteria)

Before tagging any release candidate or final release:

- [ ] **1. Test Suite Pass**: All 184+ automated unit and integration tests pass on Python 3.11 and 3.12:
  ```bash
  python3 -m pytest -v
  ```
- [ ] **2. Clean Linting**: Ruff linter reports zero warnings or errors:
  ```bash
  python3 -m ruff check .
  ```
- [ ] **3. Clean Package Build**: Source distribution and wheel build successfully without warnings:
  ```bash
  python3 -m build
  ```
- [ ] **4. Isolated Wheel Smoke Test**: Install the built wheel into a clean virtual environment and verify entry points:
  ```bash
  python3 -m venv /tmp/test_env
  /tmp/test_env/bin/pip install dist/*.whl
  /tmp/test_env/bin/aegis --help
  /tmp/test_env/bin/aegis doctor
  rm -rf /tmp/test_env
  ```
- [ ] **5. Synthetic End-to-End Demo**: Run the synthetic demo and verify 100% hash reproducibility across repeated runs:
  ```bash
  ./run.sh demo-e2e
  ```
- [ ] **6. Evaluation Suite Execution**: Execute the evaluation suite and confirm zero failures:
  ```bash
  ./run.sh evaluation run --format terminal
  ```
- [ ] **7. Repository Hygiene Audit**: Ensure no device evidence, private tokens, or generated junk are tracked:
  ```bash
  git status --porcelain
  git ls-files | grep -E "evidence/|reports/|snapshots/|\.device-dump"
  ```
- [ ] **8. Documentation Alignment**: Verify that CLI flags, examples, and schema versions in `README.md`, `docs/`, and `run.sh` match actual implementations.

---

## 4. Building Distribution Artifacts

To generate distribution artifacts locally:
```bash
# Clean previous build artifacts
rm -rf dist/ build/ src/*.egg-info/

# Build sdist and wheel
python3 -m build
```
Verify the contents of `dist/`:
```bash
ls -la dist/
# Should contain:
# aegis_android_research-0.1.0.tar.gz
# aegis_android_research-0.1.0-py3-none-any.whl
```

---

## 5. Tagging & Publication Procedure

### A. Cutting a Release Candidate Tag
Once the checklist is satisfied on `main`:
```bash
git tag -s v0.1.0-rc1 -m "Release candidate v0.1.0-rc1"
git push origin v0.1.0-rc1
```

### B. Final Release Publication
1. Maintainer reviews GitHub Actions CI runs for the release tag.
2. Maintainer inspects build artifacts and publishes the release notes.
3. If publishing to PyPI:
   ```bash
   python3 -m twine check dist/*
   python3 -m twine upload dist/*
   ```
*(Note: Never automate PyPI credential publication without explicit project owner authorization).*
