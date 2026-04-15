# Twitter-Pull → Telegram: Quick Start

✅ **Setup Complete!** The system is now running automatically.

## What's Running

**Once daily at 7am PT**, the system will:
1. 🐦 Fetch ~100 latest tweets from configured accounts and topics
2. 🤖 Summarize them using Claude AI
3. 📱 Send condensed summaries to your Telegram DM

## Test It Now

```bash
cd /home/ec2-user/twitter-pull
./run_and_send.sh
```

You should receive a DM via @kybernetikosbot (ID: 5747500729)

## Current Configuration

**Twitter Sources:**
- Accounts: karpathy, rauchg, GergelyOrosz, levie, emollick (5 tweets each)
- Topics: AI Engineering, Design Engineering, Developer Tools, Startups & Product
- Custom: AI Economics, Agent Architecture
- **Daily cap:** ~100 posts maximum

**Schedule:** Once daily at 7am PT (14:00 UTC)

**Telegram:** Sends DM to your personal chat (5747500729)

## Customize

### Change What You Track
Edit `config/feed.yaml`:
```bash
nano config/feed.yaml
```

### Change Schedule
```bash
crontab -e
# Current: 0 14 * * * (daily at 7am PT / 14:00 UTC)
# Twice daily: 0 14,20 * * * (7am PT and 1pm PT)
```

### View Logs
```bash
# Main log
tail -f logs/telegram_send.log

# Cron wrapper log
tail -f logs/cron_wrapper.log
```

## How It Works

```
┌─────────────┐
│   Cron      │ Every 30 min
│   Job       │
└──────┬──────┘
       │
       v
┌─────────────────────┐
│  run_and_send.sh    │
│                     │
│  1. main.py         │ ← Fetch tweets via GetXAPI
│     ├─ Dedup        │ ← Skip already-seen tweets
│     └─ Summarize    │ ← Claude AI summaries
│                     │
│  2. send_telegram_  │ ← Extract summaries only
│     summary.py      │
│     └─ Bot API      │ ← Send to Telegram
└─────────────────────┘
```

## Files Structure

```
twitter-pull/
├── .env                        # API keys (GetXAPI, Anthropic)
├── .env.telegram              # Telegram config
├── config/
│   └── feed.yaml              # What to track
├── digests/
│   └── YYYY-MM-DD-digest.md   # Daily digests
├── logs/
│   ├── telegram_send.log      # Detailed logs
│   └── cron_wrapper.log       # Cron execution logs
├── data/
│   └── seen_ids.db           # Deduplication database
├── main.py                    # Main twitter-pull script
├── run_and_send.sh           # Automation wrapper
└── send_telegram_summary.py  # Telegram sender

```

## Costs

- **GetXAPI**: ~$1.50/month
- **Claude API**: ~$0.10-0.50/month
- **Total**: ~$2/month

## Troubleshooting

**No messages arriving?**
- Check Telegram bot is in the group
- View logs: `tail -f logs/telegram_send.log`
- Test manually: `uv run python send_telegram_summary.py`

**All digests show "0 new tweets"?**
- Normal! Deduplication works - tweets seen recently won't repeat
- Try: `rm data/seen_ids.db` then run manually to reset

**Want immediate digest?**
- Run manually: `./run_and_send.sh`
- Or wait for next 30-min interval

## Next Cron Run

```bash
# Check next scheduled times
echo "Next 5 runs:"
date -u '+Next run at: %H:%M UTC on %Y-%m-%d'
# Runs at :00 and :30 of every hour
```

## Support

See `SETUP_NOTES.md` for detailed documentation.

Project: https://github.com/Sivolc2/twitter-pull
