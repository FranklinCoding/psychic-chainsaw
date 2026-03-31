#!/usr/bin/env bash
set -euo pipefail

echo "==> Setting up RimWorld Agent project"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate || . .venv/Scripts/activate

python -m pip install --upgrade pip

if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
fi

mkdir -p runs models data logs artifacts

echo "==> Running quick validation"
if [ -f "tests/test_config.py" ]; then
  pytest -q tests/test_config.py || true
fi

echo "==> Setup complete"
