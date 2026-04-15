#!/usr/bin/env bash
# Set up cron job to run twitter-pull every 30 minutes and send to Telegram

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_SCRIPT="$SCRIPT_DIR/run_and_send.sh"

# Make sure script is executable
chmod +x "$CRON_SCRIPT"

# Cron entry - runs every 30 minutes
CRON_ENTRY="*/30 * * * * cd $SCRIPT_DIR && $CRON_SCRIPT >> logs/cron_wrapper.log 2>&1"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -F "$CRON_SCRIPT" > /dev/null; then
    echo "Cron job already exists. Updating..."
    # Remove old entries
    (crontab -l 2>/dev/null | grep -v -F "$CRON_SCRIPT") | crontab -
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✓ Cron job added successfully!"
echo "  Schedule: Every 30 minutes"
echo "  Command: $CRON_SCRIPT"
echo ""
echo "Current crontab:"
crontab -l
echo ""
echo "Logs will be written to:"
echo "  $SCRIPT_DIR/logs/telegram_send.log"
echo "  $SCRIPT_DIR/logs/cron_wrapper.log"
echo ""
echo "To test manually, run:"
echo "  $CRON_SCRIPT"
