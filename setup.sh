#!/usr/bin/env bash
# Install dependencies. Run onboard.py afterwards for interactive setup.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

mkdir -p data digests logs

echo ""
echo "Dependencies installed. Run the setup wizard:"
echo "  source .venv/bin/activate && python onboard.py"
