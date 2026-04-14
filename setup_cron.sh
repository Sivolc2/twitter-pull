#!/usr/bin/env bash
# Run this on core-worker-aimi to install the cron job.
# It will pull tweets daily at 8am UTC and write digests to ~/twitter-pull/digests/

set -euo pipefail

REPO_DIR="$HOME/twitter-pull"
PYTHON="$REPO_DIR/.venv/bin/python"
LOG_FILE="$REPO_DIR/logs/cron.log"

mkdir -p "$REPO_DIR/logs"

# Install the cron entry (idempotent)
CRON_LINE="0 8 * * * cd $REPO_DIR && $PYTHON main.py >> $LOG_FILE 2>&1"
( crontab -l 2>/dev/null | grep -v "twitter-pull" ; echo "$CRON_LINE" ) | crontab -

echo "Cron installed:"
crontab -l | grep twitter-pull
