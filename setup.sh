#!/usr/bin/env bash
# setup.sh — one-time setup for Data Extractor (Linux / macOS).
# Creates a Python virtual environment, installs packages, and makes sure
# Ollama + the extraction model are present. Run once:
#     bash setup.sh
# (or:  chmod +x setup.sh && ./setup.sh)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=============================================="
echo "  Data Extractor - one-time setup"
echo "=============================================="
echo ""

# ---- 1. Python ---------------------------------------------------------
PYTHON=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

if [ -z "$PYTHON" ]; then
    echo "[1/3] Python 3 is not installed."
    echo "      Install it from https://www.python.org/downloads/ — on Linux you can"
    echo "      usually run:  sudo apt install python3   (or:  sudo dnf install python3)"
    echo "      then re-run setup.sh."
    exit 1
fi
echo "[1/3] Python found ($PYTHON)."

# The app needs Python 3.9+ (it uses newer language syntax).
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    PYVER="$("$PYTHON" -c 'import sys; print("%d.%d" % (sys.version_info.major, sys.version_info.minor))')"
    echo "      ERROR: Python $PYVER is too old. This app needs Python 3.9 or newer (3.11 recommended)."
    echo "      Install Python 3.9+ and re-run setup.sh."
    exit 1
fi
echo ""

# ---- 2. Virtual environment + packages ---------------------------------
echo "[2/3] Creating a virtual environment and installing packages..."
if [ ! -x ".venv/bin/python" ]; then
    "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt
echo "[2/3] Packages installed."
echo ""

# ---- 3. Ollama + model --------------------------------------------------
echo "[3/3] Checking Ollama..."
OLLAMA=""
if command -v ollama >/dev/null 2>&1; then
    OLLAMA="ollama"
fi

if [ -z "$OLLAMA" ]; then
    if command -v brew >/dev/null 2>&1; then
        echo "      Installing Ollama with Homebrew (macOS)..."
        brew install --cask ollama
    elif [ "$(uname -s)" = "Linux" ]; then
        echo "      Installing Ollama with the official installer..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    if command -v ollama >/dev/null 2>&1; then
        OLLAMA="ollama"
    fi
fi

MODEL="qwen2.5:7b-instruct"
if [ -n "$OLLAMA" ]; then
    echo "      Downloading the model '$MODEL' (a few GB, one time only)..."
    "$OLLAMA" pull "$MODEL" || {
        echo "      NOTE: model pull reported a problem. Start the Ollama app once"
        echo "      (Linux: 'ollama serve' or 'systemctl start ollama'), then re-run setup.sh."
    }
else
    echo "      Ollama not installed. Install it from https://ollama.com/download,"
    echo "      then re-run setup.sh."
fi

echo "[3/3] Ollama + model ready."
echo ""
echo "=============================================="
echo "  Setup complete! Run:  bash start.sh"
echo "=============================================="
