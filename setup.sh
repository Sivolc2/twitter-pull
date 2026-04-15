#!/usr/bin/env bash
# Install uv (if needed) and sync dependencies.
# Then run: uv run python onboard.py
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Syncing dependencies..."
uv sync

mkdir -p data digests logs

echo ""
echo "Ready. Run the setup wizard:"
echo "  uv run python onboard.py"
