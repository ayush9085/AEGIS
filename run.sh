#!/usr/bin/env bash
# AEGIS Phase One Convenience Runner Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Locate Python environment (prefer .venv if active/present)
if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    PYTHON="${SCRIPT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    echo "Error: Python 3 was not found. Please install Python 3.11+." >&2
    exit 1
fi

AEGIS_CMD=("${PYTHON}" -m aegis.cli)

print_help() {
    cat <<EOF
AEGIS Quick Runner
Usage: ./run.sh [command] [args...]

Commands:
  doctor              Check local environment, Python, and ADB status
  devices             List connected ADB devices (safe read-only discovery)
  test                Run unit test suite (pytest) and linter (ruff)
  demo                Generate a self-contained sample HTML report using synthetic fixtures
  collect <serial>    Run read-only collection against target device (output: ./reports/<serial>)
  report <file.json>  Generate self-contained HTML report from an evidence JSON document
  validate <file>     Validate an evidence JSON document against the schema
  install             Install or update the package in editable mode with development dependencies
  help                Show this help message

If no command is provided, 'doctor' and 'test' will run.
EOF
}

COMMAND="${1:-all}"

case "${COMMAND}" in
    doctor)
        "${AEGIS_CMD[@]}" doctor
        ;;
    devices)
        "${AEGIS_CMD[@]}" devices
        ;;
    test)
        echo "Running pytest..."
        "${PYTHON}" -m pytest -v
        echo ""
        echo "Running ruff check..."
        "${PYTHON}" -m ruff check .
        echo "All checks and tests passed!"
        ;;
    demo)
        DEMO_OUT="${SCRIPT_DIR}/reports/demo"
        mkdir -p "${DEMO_OUT}"
        FIXTURE="${SCRIPT_DIR}/tests/fixtures/sample_evidence.json"
        REPORT_OUT="${DEMO_OUT}/sample_report.html"

        echo "Validating synthetic evidence fixture..."
        "${AEGIS_CMD[@]}" validate "${FIXTURE}"
        echo ""
        echo "Generating standalone HTML report..."
        "${AEGIS_CMD[@]}" report "${FIXTURE}" --format html --out "${REPORT_OUT}"
        echo ""
        echo "Demo report created successfully:"
        echo "  ${REPORT_OUT}"
        if [[ "$(uname)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
            echo "Tip: Run 'open \"${REPORT_OUT}\"' to view the report in your browser."
        fi
        ;;
    collect)
        if [[ $# -lt 2 ]]; then
            echo "Error: Device serial required." >&2
            echo "Usage: ./run.sh collect <serial> [output_directory]" >&2
            exit 2
        fi
        SERIAL="$2"
        OUT_DIR="${3:-${SCRIPT_DIR}/reports/${SERIAL}}"
        "${AEGIS_CMD[@]}" collect --device "${SERIAL}" --out "${OUT_DIR}"
        ;;
    report)
        if [[ $# -lt 2 ]]; then
            echo "Error: Evidence JSON path required." >&2
            echo "Usage: ./run.sh report <path-to-evidence.json> [output_html]" >&2
            exit 2
        fi
        EVIDENCE="$2"
        OUT_HTML="${3:-}"
        if [[ -n "${OUT_HTML}" ]]; then
            "${AEGIS_CMD[@]}" report "${EVIDENCE}" --format html --out "${OUT_HTML}"
        else
            "${AEGIS_CMD[@]}" report "${EVIDENCE}" --format html
        fi
        ;;
    validate)
        if [[ $# -lt 2 ]]; then
            echo "Error: Evidence JSON path required." >&2
            echo "Usage: ./run.sh validate <path-to-evidence.json>" >&2
            exit 2
        fi
        "${AEGIS_CMD[@]}" validate "$2"
        ;;
    install)
        echo "Installing AEGIS in editable mode with dev dependencies..."
        "${PYTHON}" -m pip install --upgrade pip
        "${PYTHON}" -m pip install -e ".[dev]"
        ;;
    help|--help|-h)
        print_help
        ;;
    all)
        echo "=== Environment Preflight ==="
        "${AEGIS_CMD[@]}" doctor
        echo ""
        echo "=== Running Automated Tests & Lint ==="
        "${PYTHON}" -m pytest
        "${PYTHON}" -m ruff check .
        echo ""
        echo "=== Generating Demo Report ==="
        DEMO_OUT="${SCRIPT_DIR}/reports/demo"
        mkdir -p "${DEMO_OUT}"
        "${AEGIS_CMD[@]}" report "${SCRIPT_DIR}/tests/fixtures/sample_evidence.json" --format html --out "${DEMO_OUT}/sample_report.html"
        echo ""
        echo "AEGIS ready! Run './run.sh help' for command options."
        ;;
    *)
        echo "Unknown command: ${COMMAND}" >&2
        print_help
        exit 1
        ;;
esac
