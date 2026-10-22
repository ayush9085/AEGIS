#!/usr/bin/env bash
# AEGIS Developer Runner Script
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

🛡️  AEGIS — Android Exploration, Guardrails, Intelligence & Security
Developer Quick-Runner

Usage: ./run.sh [command] [options]

Core Commands:
  menu                Launch interactive guided menu (easy mode for developers)
  scan                Auto-detect phone, collect evidence, & open report in browser
  collect [serial]    Collect evidence (auto-detects phone if only 1 is connected)
  devices             List connected phones and check authorization status
  doctor              Check host setup, Python, and Android Platform Tools (ADB)
  snapshot [file]     Create versioned snapshot with canonical SHA-256 hash
  diff <snap1> <snap2> Run deterministic semantic diff between two snapshots
  firmware [inspect]  Offline analysis of boot.img, sparse, or OTA zip
  research [analyze]  Correlate evidence reports, build graph & evaluate rules
  evaluation [run]    Run research validation suite against ground-truth corpus
  demo                Preview a sample report with synthetic data (no phone needed)
  report [file.json]  Generate HTML report (defaults to your latest collection)
  validate [file]     Check evidence JSON against the schema
  test                Run unit test suite (pytest) and linter (ruff)
  install             Install/update AEGIS in editable development mode
  help                Show this help message

Examples:
  ./run.sh                      # Launch guided interactive menu
  ./run.sh scan                 # One-step collection and report viewing
  ./run.sh snapshot             # Save snapshot from latest evidence
  ./run.sh diff snap1.json snap2.json # Compare two snapshots
  ./run.sh doctor               # Check your ADB setup
  ./run.sh demo                 # Explore report UI without any phone

EOF
}

COMMAND="${1:-}"

if [[ -z "${COMMAND}" ]]; then
    if [[ -t 0 && -t 1 ]]; then
        exec "${AEGIS_CMD[@]}" menu
    else
        exec "${AEGIS_CMD[@]}" scan
    fi
fi

case "${COMMAND}" in
    menu)
        "${AEGIS_CMD[@]}" menu
        ;;
    doctor)
        "${AEGIS_CMD[@]}" doctor
        ;;
    devices)
        "${AEGIS_CMD[@]}" devices
        ;;
    scan)
        echo "Starting AEGIS scan (auto-detecting device)..."
        "${AEGIS_CMD[@]}" collect --open "${@:2}"
        ;;
    collect)
        if [[ $# -ge 2 ]]; then
            SERIAL="$2"
            OUT_DIR="${3:-}"
            if [[ -n "${OUT_DIR}" ]]; then
                "${AEGIS_CMD[@]}" collect --device "${SERIAL}" --out "${OUT_DIR}"
            else
                "${AEGIS_CMD[@]}" collect --device "${SERIAL}"
            fi
        else
            # Auto-detect connected device
            "${AEGIS_CMD[@]}" collect "${@:2}"
        fi
        ;;
    snapshot)
        "${AEGIS_CMD[@]}" snapshot "${@:2}"
        ;;
    diff)
        "${AEGIS_CMD[@]}" diff "${@:2}"
        ;;
    firmware)
        "${AEGIS_CMD[@]}" firmware "${@:2}"
        ;;
    research)
        "${AEGIS_CMD[@]}" research "${@:2}"
        ;;
    evaluation)
        "${AEGIS_CMD[@]}" evaluation "${@:2}"
        ;;
    report)
        EVIDENCE="${2:-}"
        OUT_HTML="${3:-}"
        if [[ -n "${EVIDENCE}" && -n "${OUT_HTML}" ]]; then
            "${AEGIS_CMD[@]}" report "${EVIDENCE}" --format html --out "${OUT_HTML}" --open
        elif [[ -n "${EVIDENCE}" ]]; then
            "${AEGIS_CMD[@]}" report "${EVIDENCE}" --format html --open
        else
            # Auto-detect latest report
            "${AEGIS_CMD[@]}" report --open
        fi
        ;;
    validate)
        if [[ $# -ge 2 ]]; then
            "${AEGIS_CMD[@]}" validate "$2"
        else
            "${AEGIS_CMD[@]}" validate
        fi
        ;;
    demo)
        "${AEGIS_CMD[@]}" demo --open
        ;;
    test)
        echo "Running pytest..."
        "${PYTHON}" -m pytest -v
        echo ""
        echo "Running ruff check..."
        "${PYTHON}" -m ruff check .
        echo ""
        echo "All checks and tests passed!"
        ;;
    install)
        echo "Installing AEGIS in editable mode with dev dependencies..."
        "${PYTHON}" -m pip install --upgrade pip
        "${PYTHON}" -m pip install -e ".[dev]"
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo "Unknown command: ${COMMAND}" >&2
        print_help
        exit 1
        ;;
esac
