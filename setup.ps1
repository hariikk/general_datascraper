# setup.ps1 — one-time setup for ScrapeLite.
# Creates a Python virtual environment, installs packages, and makes sure
# Ollama + the extraction model are present. Run it once (or double-click
# setup.bat, which runs this file).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Refresh-Path {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

Write-Host ""
Write-Host "=============================================="
Write-Host "  ScrapeLite - one-time setup"
Write-Host "=============================================="
Write-Host ""

# ---- 1. Python ---------------------------------------------------------
$python = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $python = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $python = "py" }

if ($null -eq $python) {
    Write-Host "[1/3] Python is not installed."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "      Installing Python 3.11 with winget..."
        winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        Refresh-Path
        if (Get-Command python -ErrorAction SilentlyContinue) { $python = "python" }
        elseif (Get-Command py -ErrorAction SilentlyContinue) { $python = "py" }
    }
    if ($null -eq $python) {
        Write-Host "      ERROR: Python could not be installed automatically."
        Write-Host "      Install it from https://www.python.org/downloads/"
        Write-Host "      (IMPORTANT: tick 'Add python.exe to PATH' during install),"
        Write-Host "      then run setup.bat again."
        exit 1
    }
}
Write-Host "[1/3] Python found ($python)."

# The app needs Python 3.9+ (it uses newer language syntax). Warn clearly if the
# installed Python is too old, instead of crashing later with a confusing error.
$pyVer = (& $python -c "import sys; print('%d.%d' % (sys.version_info.major, sys.version_info.minor))").Trim()
if ([version]$pyVer -lt [version]"3.9") {
    Write-Host "      ERROR: Python $pyVer is too old. This app needs Python 3.9 or newer (3.11 recommended)."
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Python $pyVer was found, but this app needs Python 3.9 or newer (3.11 recommended).`n`nPlease install Python 3.11 from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then run setup.bat again.",
        "Python too old",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 1
}
Write-Host ""

# ---- 2. Virtual environment + packages ---------------------------------
Write-Host "[2/3] Creating a virtual environment and installing packages..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      ERROR: could not create the virtual environment."
        exit 1
    }
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERROR: package install failed. Check your internet connection and re-run setup.bat."
    exit 1
}
Write-Host "[2/3] Packages installed."
Write-Host ""

# ---- 3. Ollama + model --------------------------------------------------
Write-Host "[3/3] Checking Ollama..."
$ollama = $null
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $ollama = "ollama"
} else {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $candidate) { $ollama = $candidate }
}

if ($null -eq $ollama) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "      Ollama is not installed. Installing with winget..."
        winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
        Refresh-Path
        if (Get-Command ollama -ErrorAction SilentlyContinue) { $ollama = "ollama" }
        else {
            $candidate = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
            if (Test-Path $candidate) { $ollama = $candidate }
        }
    } else {
        Write-Host "      Ollama is not installed and winget is unavailable."
        Write-Host "      Install Ollama from https://ollama.com/download and re-run setup.bat."
    }
}

$model = "qwen2.5:7b-instruct"
if ($null -ne $ollama) {
    Write-Host "      Downloading the model '$model' (a few GB, one time only)..."
    & $ollama pull $model
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      NOTE: model pull reported a problem. Open the Ollama app once,"
        Write-Host "      then re-run setup.bat (or run:  ollama pull $model)."
    }
} else {
    Write-Host "      Skipping model download - install Ollama first, then re-run setup.bat."
}

Write-Host "[3/3] Ollama + model ready."
Write-Host ""
Write-Host "=============================================="
Write-Host "  Setup complete! Double-click start.bat to run."
Write-Host "=============================================="
