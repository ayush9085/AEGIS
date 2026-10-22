#!/usr/bin/env bash
# ==============================================================================
# AEGIS Synthetic End-to-End Demo & Reproducibility Verification
# ==============================================================================
# Demonstrates AEGIS Phases 1–5 without requiring a physical Android device,
# live ADB connection, or proprietary firmware binaries.
# Operates strictly offline, writes only to a local isolated directory, and
# verifies deterministic report reproducibility.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

# Locate Python binary
if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    PYTHON="${SCRIPT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    echo "Error: Python 3 was not found." >&2
    exit 1
fi

DEMO_DIR=$(mktemp -d /tmp/aegis_demo_XXXXXX)
trap 'rm -rf "${DEMO_DIR}"' EXIT

echo "=============================================================================="
echo "🛡️  AEGIS — End-to-End Synthetic Demo & Reproducibility Runner"
echo "=============================================================================="
echo "Workspace:     ${SCRIPT_DIR}"
echo "Python:        $(${PYTHON} --version)"
echo "Isolated Temp: ${DEMO_DIR}"
echo "Network:       OFFLINE (Zero network calls allowed)"
echo "Device:        MOCKED / SYNTHETIC FIXTURES ONLY"
echo "------------------------------------------------------------------------------"

# Step 1: Doctor environment check
echo -e "\n[1/5] Checking environment prerequisites..."
"${PYTHON}" -m aegis.cli doctor

# Step 2: Phase 2 Snapshots & Semantic Diff
echo -e "\n[2/5] Creating evidence snapshots and running semantic diff..."
"${PYTHON}" -m aegis.cli snapshot tests/fixtures/sample_evidence.json \
    --out "${DEMO_DIR}/baseline_snap.json" \
    --overwrite \
    --notes "Baseline synthetic M11 snapshot"

"${PYTHON}" -m aegis.cli snapshot tests/fixtures/sample_evidence_updated.json \
    --out "${DEMO_DIR}/updated_snap.json" \
    --overwrite \
    --notes "Updated synthetic M11 snapshot"

"${PYTHON}" -m aegis.cli diff "${DEMO_DIR}/baseline_snap.json" "${DEMO_DIR}/updated_snap.json" \
    --format terminal

"${PYTHON}" -m aegis.cli diff "${DEMO_DIR}/baseline_snap.json" "${DEMO_DIR}/updated_snap.json" \
    --format html \
    --out "${DEMO_DIR}/diff_report.html" \
    --overwrite

# Step 3: Phase 4 Research Analysis & Evidence Graph
echo -e "\n[3/5] Correlating multi-source evidence and evaluating research rules..."
"${PYTHON}" -m aegis.cli research analyze tests/fixtures/sample_evidence.json \
    --format terminal \
    --out "${DEMO_DIR}/research_report.json" \
    --overwrite

"${PYTHON}" -m aegis.cli research validate "${DEMO_DIR}/research_report.json"

"${PYTHON}" -m aegis.cli research report "${DEMO_DIR}/research_report.json" \
    --format html \
    --out "${DEMO_DIR}/research_report.html" \
    --overwrite

# Step 4: Phase 5 Evaluation Runner
echo -e "\n[4/5] Executing evaluation suite across ground-truth corpus..."
"${PYTHON}" -m aegis.cli evaluation run \
    --format terminal \
    --out "${DEMO_DIR}/evaluation_report_run1.json" \
    --overwrite

"${PYTHON}" -m aegis.cli evaluation validate "${DEMO_DIR}/evaluation_report_run1.json"

# Step 5: Reproducibility verification across 2 consecutive runs
echo -e "\n[5/5] Verifying byte-for-byte report reproducibility..."
"${PYTHON}" -m aegis.cli evaluation run \
    --format json \
    --out "${DEMO_DIR}/evaluation_report_run2.json" \
    --overwrite >/dev/null

HASH1=$("${PYTHON}" -c "
import json
with open('${DEMO_DIR}/evaluation_report_run1.json') as f:
    d = json.load(f)
print(d['reproducibility_hash'])
")

HASH2=$("${PYTHON}" -c "
import json
with open('${DEMO_DIR}/evaluation_report_run2.json') as f:
    d = json.load(f)
print(d['reproducibility_hash'])
")

echo "  Run 1 Canonical Hash: ${HASH1}"
echo "  Run 2 Canonical Hash: ${HASH2}"

if [[ "${HASH1}" == "${HASH2}" && -n "${HASH1}" ]]; then
    echo "  ✅ Reproducibility Verified: Hashes match exactly across separate executions!"
else
    echo "  ❌ Reproducibility Failure: Mismatched execution hashes." >&2
    exit 1
fi

echo "=============================================================================="
echo "🎉 Synthetic End-to-End Demo Completed Successfully!"
echo "   All Phases 1–5 subsystems verified with 100% offline synthetic data."
echo "=============================================================================="
