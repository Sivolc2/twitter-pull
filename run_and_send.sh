#!/usr/bin/env bash
# Run twitter-pull and send digest to Telegram via OpenClaw

set -euo pipefail
cd "$(dirname "$0")"

# Log file
LOG_FILE="logs/telegram_send.log"
mkdir -p logs

# Timestamp
echo "=== Run started at $(date -u '+%Y-%m-%d %H:%M:%S UTC') ===" | tee -a "$LOG_FILE"

# Run twitter-pull (generates digest markdown)
echo "Running twitter-pull..." | tee -a "$LOG_FILE"
uv run python main.py 2>&1 | tee -a "$LOG_FILE"

# Check if digest was generated
if [ ! -d "digests" ] || [ -z "$(ls -A digests 2>/dev/null)" ]; then
    echo "No digest generated, skipping Telegram send" | tee -a "$LOG_FILE"
    exit 0
fi

# Send condensed summary to Telegram via Bot API
echo "Sending to Telegram..." | tee -a "$LOG_FILE"
uv run python send_telegram_summary.py 2>&1 | tee -a "$LOG_FILE"

echo "=== Run completed at $(date -u '+%Y-%m-%d %H:%M:%S UTC') ===" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
