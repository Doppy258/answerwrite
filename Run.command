#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Open Setup.command first."
  read -r -p "Press Return to close."
  exit 1
fi
.venv/bin/python -m answerwrite
status=$?
if [ "$status" -ne 0 ]; then
  printf '\nThe app stopped. Read the message above.\n'
  read -r -p "Press Return to close."
fi
exit "$status"
