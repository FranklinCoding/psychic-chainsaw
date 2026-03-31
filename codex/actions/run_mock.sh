#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source .venv/bin/activate || . .venv/Scripts/activate

python -m trainer.main --profile mock