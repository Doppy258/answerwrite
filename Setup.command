#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
trap 'echo "Setup stopped. Read the error above."; read -r -p "Press Return to close."' ERR
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v python3 >/dev/null; then
  echo "Install Python 3.14 from python.org. Then run this file again."
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10 or newer is required"'
if ! python3 -c 'import tkinter' 2>/dev/null; then
  if command -v brew >/dev/null; then
    PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 brew install "python-tk@$PY_VERSION"
  else
    echo "Install Python from python.org. That installer includes Tk."
    exit 1
  fi
fi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
chmod 600 .env
printf '\nSetup is complete. Add your settings to .env, then open Run.command.\n'
read -r -p "Press Return to close."
