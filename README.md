# twitter-pull

Periodic Twitter/X data pipeline that pulls tweets on topics of interest and summarizes them into Markdown digests using Claude.

## What it does

- **Keyword search**: AI updates, new model releases, building-with-AI tips, news
- **Account timelines**: Pulls recent tweets from key people you follow (Karpathy, sama, PG, etc.)
- **Deduplication**: SQLite-backed, skips tweets seen in the last 7 days
- **Summarization**: Claude API condenses each topic into a structured briefing
- **Output**: Dated Markdown files, optionally synced to your Obsidian vault

## Cost

| Backend | Cost | Notes |
|---|---|---|
| **TwitterAPI.io** (default) | ~$1–3/month | $0.15/1,000 tweets, REST API |
| **twscrape** | Free | Uses Twitter's internal API — fragile, needs real accounts |

## Setup

```bash
git clone https://github.com/Sivolc2/twitter-pull
cd twitter-pull
bash setup.sh
```

Then edit `config/settings.local.yaml` (created by setup.sh):

```yaml
twitterapi_io:
  api_key: "your-key-from-twitterapi.io"

summarizer:
  api_key: "your-anthropic-api-key"
```

## Configure topics and accounts

Edit `config/topics.yaml`:
- Add/remove keyword queries under `topics:`
- Add Twitter usernames under `accounts.key_people:`
- Optionally set `obsidian_dir` under `output:` to sync digests to Obsidian

## Run

```bash
source .venv/bin/activate

# test without writing output
python main.py --dry-run

# run everything
python main.py

# only AI topic
python main.py --topics ai_updates

# only account timelines
python main.py --accounts-only
```

## Schedule (cron)

```bash
bash setup_cron.sh   # installs daily 8am UTC cron job
```

## Architecture

```
cron (daily)
  └── main.py
        ├── fetcher (TwitterAPI.io or twscrape)
        │     ├── search() — keyword queries per topic
        │     └── timeline() — per-account tweet pull
        ├── Deduplicator (SQLite, 7-day window)
        ├── Summarizer (Claude API, batched by topic)
        └── write_digest() → digests/YYYY-MM-DD-twitter-digest.md
                           → Obsidian vault (optional)
```

## Switching to twscrape (free)

In `config/settings.local.yaml`:
```yaml
fetcher: twscrape
```

Then add Twitter accounts:
```bash
pip install twscrape
echo "username:password:email:emailpassword" > accounts.txt
twscrape add_accounts accounts.txt
twscrape login_all
```

Note: twscrape may break when X changes internal APIs. Expect occasional maintenance.
