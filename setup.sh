#!/usr/bin/env bash
# One-shot setup script for core-worker-aimi (or any Linux host).
# Run: bash setup.sh

set -euo pipefail

echo "==> Setting up twitter-pull"
cd "$(dirname "$0")"

# create virtualenv
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# create data dir
mkdir -p data digests logs

# copy settings template if not already present
if [ ! -f config/settings.local.yaml ]; then
  cat > config/settings.local.yaml <<'EOF'
# Local overrides — this file is gitignored
fetcher: twitterapi_io

twitterapi_io:
  api_key: "PASTE_YOUR_TWITTERAPI_IO_KEY_HERE"

summarizer:
  api_key: "PASTE_YOUR_ANTHROPIC_API_KEY_HERE"

output:
  # Uncomment to sync to Obsidian:
  # obsidian_dir: "~/Documents/Argos/Twitter Digests"
EOF
  echo "Created config/settings.local.yaml — fill in your API keys"
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit config/settings.local.yaml and add your API keys"
echo "  2. Edit config/topics.yaml to set your topics and followed accounts"
echo "  3. Test with: source .venv/bin/activate && python main.py --dry-run"
echo "  4. Schedule with: bash setup_cron.sh"
