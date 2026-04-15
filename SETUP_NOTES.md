# Twitter-Pull → Telegram Setup

This repository has been configured to automatically pull Twitter digests and send them to Telegram every 30 minutes via OpenClaw.

## Setup Summary

### 1. Repository Cloned
```bash
git clone git@github.com:Sivolc2/twitter-pull.git
cd twitter-pull
```

### 2. Dependencies Installed
- Used `uv` package manager
- Installed all required Python dependencies
- Added httpx for HTTP requests

### 3. API Keys Configured
Created `.env` file with:
- `GETXAPI_KEY` - For fetching tweets
- `ANTHROPIC_API_KEY` - For AI summarization with Claude

### 4. Telegram Integration
Created two sending scripts:

**`send_telegram_summary.py`** (recommended - used by cron):
- Sends only AI-generated summaries
- Excludes individual tweet text
- Much more concise (3 messages vs 27)
- Rate-limited to avoid Telegram API throttling

**`send_telegram_bot.py`** (full version):
- Sends complete digest with all tweet text
- May hit rate limits with large digests

Configuration in `.env.telegram`:
- `TELEGRAM_CHAT_ID=-5155248703` - Target Telegram group
- `TELEGRAM_BOT_TOKEN` - Bot authentication

### 5. Automated Script
Created `run_and_send.sh` that:
1. Runs twitter-pull to fetch and summarize tweets
2. Generates markdown digest in `digests/` directory
3. Sends condensed summary to Telegram
4. Logs everything to `logs/telegram_send.log`

### 6. Cron Job
Scheduled to run every 30 minutes:
```cron
*/30 * * * * cd /home/ec2-user/twitter-pull && /home/ec2-user/twitter-pull/run_and_send.sh >> logs/cron_wrapper.log 2>&1
```

## Usage

### Manual Test
```bash
cd /home/ec2-user/twitter-pull
./run_and_send.sh
```

### View Logs
```bash
# Main application log
tail -f logs/telegram_send.log

# Cron wrapper log
tail -f logs/cron_wrapper.log
```

### Generate Test Digest
```bash
# Dry run (no file output)
uv run python main.py --dry-run

# Generate digest for specific presets
uv run python main.py --presets ai_news

# Full run
uv run python main.py
```

### Send to Telegram
```bash
# Send summary (recommended)
uv run python send_telegram_summary.py

# Send full digest (may hit rate limits)
uv run python send_telegram_bot.py
```

## Configuration

### Customize Feed
Edit `config/feed.yaml` to change:
- Twitter accounts to follow
- Topic presets (ai_news, startups, etc.)
- Custom topic searches

### Change Schedule
Edit cron job:
```bash
crontab -e
```

Current schedule: Every 30 minutes (`*/30 * * * *`)

Other examples:
- Every hour: `0 * * * *`
- Every 2 hours: `0 */2 * * *`
- Twice daily (9am, 9pm UTC): `0 9,21 * * *`

### Telegram Recipients
Edit `.env.telegram` to change:
- `TELEGRAM_CHAT_ID` - Target chat/group ID
- `TELEGRAM_BOT_TOKEN` - Bot credentials

## Files Created

### Scripts
- `send_telegram_summary.py` - Sends condensed summaries
- `send_telegram_bot.py` - Sends full digest
- `send_to_telegram.py` - OpenClaw HTTP API version (not used)
- `run_and_send.sh` - Main automation script
- `setup_cron_telegram.sh` - Cron setup script

### Configuration
- `.env` - API keys for GetXAPI and Anthropic
- `.env.telegram` - Telegram configuration

### Documentation
- `SETUP_NOTES.md` - This file

## Deduplication
Twitter-pull uses SQLite to track seen tweet IDs:
- Database: `data/seen_ids.db`
- Window: 7 days (tweets older than 7 days can appear again)
- This prevents duplicate tweets in consecutive runs

## Costs
- GetXAPI: ~$1.50/month for typical usage
- Claude API: ~$0.10-0.50/month for summarization
- Total: ~$2/month

## Troubleshooting

### No tweets in digest
- Check deduplication database: `data/seen_ids.db`
- All tweets may have been seen recently
- Try: `uv run python main.py --dry-run` to preview

### Telegram not receiving messages
- Check bot token in `.env.telegram`
- Verify chat ID is correct
- Check logs: `tail -f logs/telegram_send.log`
- Test manually: `uv run python send_telegram_summary.py`

### Rate limit errors from Telegram
- Script includes 2-second delays between chunks
- If still hitting limits, increase delay in `send_telegram_summary.py`
- Or use summary version (already configured)

### Cron job not running
- Check cron is running: `systemctl status cron` or `service crond status`
- View cron logs: `grep CRON /var/log/syslog` or `tail -f logs/cron_wrapper.log`
- Test manually first: `./run_and_send.sh`

## Next Steps

1. **Test the setup**: Wait for next 30-minute interval or run manually
2. **Monitor logs**: Check `logs/` directory for any errors
3. **Customize feed**: Edit `config/feed.yaml` for your interests
4. **Adjust schedule**: Modify cron if 30 minutes is too frequent

## Resources
- Twitter-pull GitHub: https://github.com/Sivolc2/twitter-pull
- GetXAPI: https://getxapi.com
- Anthropic API: https://console.anthropic.com
