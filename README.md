# twitter-pull

A personal Twitter/X digest generator. Pulls tweets on topics you care about, summarizes them with Claude, and writes dated Markdown files — twice a day, automatically.

## What you get

- **Topic digests** — AI news, startup funding, tech releases, or any custom keywords
- **Account timelines** — tweets from people you follow, summarized as a group
- **AI summaries** — Claude distills each topic into key themes, notable signals, and a one-liner
- **Deduplication** — runs twice daily without repeating what you already saw
- **Markdown output** — readable anywhere; optional sync to Obsidian

## Cost

| Component | Cost |
|---|---|
| Twitter data | ~$1.50/month ([GetXAPI](https://getxapi.com)) |
| Summarization | ~$0.10–0.50/month (Claude API) |
| Hosting | Free if you have a server; otherwise ~$5/mo VPS |

## Quickstart

```bash
git clone https://github.com/Sivolc2/twitter-pull
cd twitter-pull
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python onboard.py
```

`onboard.py` walks you through everything interactively:
1. Paste your API keys
2. Pick topic presets from a menu
3. Choose accounts to follow
4. Optionally connect your Obsidian vault
5. Test fetch + install cron

**That's it.** Your first digest runs immediately, then automatically every day.

## Configuring your feed

After setup, edit **`config/feed.yaml`** — this is the only file you need to touch:

```yaml
# Who to follow — their tweets are pulled daily and summarized together
accounts:
  - karpathy
  - paulg
  - sama

# Topic presets — pick from the list below
presets:
  - ai_news
  - startups

# Your own topics — no query syntax needed
custom_topics:
  - name: "Robotics"
    any: ["robotics", "humanoid robot", "Figure AI", "Boston Dynamics"]
    min_likes: 20
```

**Available presets:**

| Preset | What it covers |
|---|---|
| `ai_news` | Model releases, research papers, industry moves |
| `ai_building` | Coding tools, RAG, agents, tutorials |
| `startups` | Funding rounds, YC, founder insights |
| `tech_news` | Big tech, open source, developer tools |
| `crypto` | DeFi, protocols, regulation |
| `news` | Breaking world news |
| `science` | Research papers, biotech, climate |
| `geopolitics` | International relations, policy |

After editing `feed.yaml`, test with:
```bash
python main.py --dry-run
```

## Running manually

```bash
source .venv/bin/activate

python main.py                        # run everything, write digest
python main.py --dry-run              # preview without writing
python main.py --presets ai_news      # one preset only
python main.py --accounts-only        # only account timelines
python main.py --topics-only          # only keyword searches
```

Digests are written to `digests/YYYY-MM-DD-twitter-digest.md`.

## Architecture

```
cron (twice daily)
  └── main.py
        ├── .env                  ← API keys (gitignored)
        ├── config/feed.yaml      ← your accounts + topics
        ├── config/settings.yaml  ← backend/model settings
        ├── config/presets.yaml   ← query definitions for presets
        │
        ├── Fetcher (GetXAPI)     ← pulls tweets
        ├── Deduplicator (SQLite) ← 7-day rolling dedup window
        ├── Summarizer (Claude)   ← per-topic AI digest
        └── write_digest()        → digests/YYYY-MM-DD-twitter-digest.md
                                  → Obsidian vault (optional)
```

## Switching fetcher backends

In `config/settings.yaml`, change `fetcher:` and set the corresponding key in `.env`:

| Backend | Cost | Notes |
|---|---|---|
| `getxapi` (default) | ~$1.50/mo | Recommended |
| `twitterapi_io` | ~$4.50/mo | Reliable fallback |
| `twscrape` | Free | Needs real Twitter accounts; breaks periodically |

## Logs

```bash
tail -f logs/cron.log    # watch live
```
