#!/usr/bin/env bash
# start.sh — launch the Data Extractor web app (Linux / macOS).
# Run:  bash start.sh   (or:  chmod +x start.sh && ./start.sh)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x ".venv/bin/python" ]; then
    echo "Virtual environment not found - running setup first..."
    echo ""
    bash "$SCRIPT_DIR/setup.sh"
fi

if [ ! -x ".venv/bin/python" ]; then
    echo ""
    echo "Setup did not complete. Please run 'bash setup.sh' and read the messages."
    exit 1
fi

.venv/bin/python app.py
