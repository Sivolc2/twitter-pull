#!/usr/bin/env python3
"""
twitter-pull — periodic Twitter/X digest generator

Usage:
  python main.py                          # run everything in feed.yaml
  python main.py --presets ai_news        # run specific presets only
  python main.py --accounts-only          # only pull account timelines
  python main.py --topics-only            # only run topic searches
  python main.py --dry-run                # fetch and summarize, skip writing file
"""
from __future__ import annotations
import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("twitter-pull")

ROOT = Path(__file__).parent


def load_env() -> None:
    """Load .env file if present (falls back to environment variables)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # manual parse if python-dotenv not installed
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def load_config():
    load_env()

    with open(ROOT / "config" / "settings.yaml") as f:
        settings = yaml.safe_load(f)

    with open(ROOT / "config" / "feed.yaml") as f:
        feed = yaml.safe_load(f)

    with open(ROOT / "config" / "presets.yaml") as f:
        presets_cfg = yaml.safe_load(f)

    # inject API keys from environment
    backend = settings.get("fetcher", "getxapi")
    if backend == "getxapi":
        settings.setdefault("getxapi", {})["api_key"] = os.environ.get("GETXAPI_KEY", "")
    elif backend == "twitterapi_io":
        settings.setdefault("twitterapi_io", {})["api_key"] = os.environ.get("TWITTERAPI_IO_KEY", "")

    settings["summarizer"]["api_key"] = os.environ.get("ANTHROPIC_API_KEY", "") or \
                                         os.environ.get("OPENAI_API_KEY", "")

    return settings, feed, presets_cfg


def build_fetcher(settings: dict):
    backend = settings.get("fetcher", "getxapi")
    if backend == "getxapi":
        from src.fetchers.getxapi import GetXAPIFetcher
        cfg = settings["getxapi"]
        if not cfg.get("api_key"):
            sys.exit("ERROR: GETXAPI_KEY not set. Add it to .env or set the environment variable.")
        return GetXAPIFetcher(api_key=cfg["api_key"], rate_limit_pause=cfg.get("rate_limit_pause", 1.0))
    elif backend == "twitterapi_io":
        from src.fetchers.twitterapi_io import TwitterAPIioFetcher
        cfg = settings["twitterapi_io"]
        if not cfg.get("api_key"):
            sys.exit("ERROR: TWITTERAPI_IO_KEY not set. Add it to .env or set the environment variable.")
        return TwitterAPIioFetcher(api_key=cfg["api_key"], base_url=cfg["base_url"],
                                   rate_limit_pause=cfg.get("rate_limit_pause", 1.0))
    elif backend == "twscrape":
        from src.fetchers.twscrape_fetcher import TwscrapeFetcher
        return TwscrapeFetcher(accounts_db=settings["twscrape"]["accounts_db"])
    else:
        sys.exit(f"ERROR: Unknown fetcher backend '{backend}'. Check config/settings.yaml.")


def custom_topic_to_query(topic: dict) -> str:
    """Convert a plain-English custom topic dict into a Twitter search query."""
    parts = []
    any_terms = topic.get("any", [])
    require_terms = topic.get("require", [])
    exclude_terms = topic.get("exclude", [])

    if any_terms:
        quoted = [f'"{t}"' if " " in t else t for t in any_terms]
        parts.append(f"({' OR '.join(quoted)})")
    for t in require_terms:
        parts.append(f'"{t}"' if " " in t else t)
    for t in exclude_terms:
        parts.append(f'-"{t}"' if " " in t else f"-{t}")

    min_likes = topic.get("min_likes", 10)
    parts.append(f"lang:en -is:retweet min_faves:{min_likes}")
    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Twitter/X digest generator")
    parser.add_argument("--presets", nargs="*", help="run only these preset names")
    parser.add_argument("--accounts-only", action="store_true")
    parser.add_argument("--topics-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="print output, don't write file")
    args = parser.parse_args()

    settings, feed, presets_cfg = load_config()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    from src.processors.dedup import Deduplicator
    from src.processors.summarizer import Summarizer
    from src.outputs.markdown import write_digest

    storage = settings["storage"]
    dedup = Deduplicator(storage["seen_ids_db"], storage["dedup_window_days"])

    sum_cfg = settings["summarizer"]
    summarizer = Summarizer(
        provider=sum_cfg["provider"],
        model=sum_cfg["model"],
        api_key=sum_cfg.get("api_key", ""),
        max_tokens=sum_cfg["max_tokens"],
        batch_size=sum_cfg["batch_size"],
    )

    fetcher = build_fetcher(settings)
    results = []

    # ── topic searches ──────────────────────────────────────────────────────
    if not args.accounts_only:
        preset_filter = set(args.presets) if args.presets else None
        all_presets = presets_cfg.get("presets", {})

        # built-in presets from feed.yaml
        for preset_name in feed.get("presets", []):
            if preset_filter and preset_name not in preset_filter:
                continue
            if preset_name not in all_presets:
                log.warning("unknown preset '%s' — check config/presets.yaml", preset_name)
                continue
            preset = all_presets[preset_name]
            label = preset["label"]
            log.info("fetching preset: %s", label)
            all_tweets = []
            for query in preset["queries"]:
                tweets = fetcher.search(query, max_results=preset.get("max_results", 60))
                log.info("  '%s': %d tweets", query[:70], len(tweets))
                all_tweets.extend(tweets)
            new = dedup.filter_new(all_tweets)
            log.info("%s: %d new tweets", label, len(new))
            results.append(summarizer.summarize(new, label, date_str))

        # custom topics from feed.yaml
        for topic in feed.get("custom_topics", []):
            name = topic.get("name", "Custom")
            if preset_filter and name not in preset_filter:
                continue
            query = custom_topic_to_query(topic)
            log.info("fetching custom topic: %s", name)
            tweets = fetcher.search(query, max_results=topic.get("max_results", 50))
            log.info("  %d tweets", len(tweets))
            new = dedup.filter_new(tweets)
            results.append(summarizer.summarize(new, name, date_str))

    # ── account timelines ───────────────────────────────────────────────────
    if not args.topics_only:
        accounts = feed.get("accounts", [])
        max_per = settings.get("accounts", {}).get("max_results_per_account", 20)
        if accounts:
            log.info("fetching %d account timelines", len(accounts))
            all_tweets = []
            for username in accounts:
                tweets = fetcher.timeline(username, max_results=max_per)
                log.info("  @%s: %d tweets", username, len(tweets))
                all_tweets.extend(tweets)
            new = dedup.filter_new(all_tweets)
            log.info("accounts: %d new tweets", len(new))
            results.append(summarizer.summarize(new, "Key People", date_str))

    fetcher.close()
    dedup.close()

    if not results:
        log.info("nothing to write")
        return

    if args.dry_run:
        for r in results:
            print(f"\n{'='*60}\n{r.topic_label} ({r.tweet_count} tweets)\n{r.summary}")
        return

    output_cfg = feed.get("output", {})
    digest_path = write_digest(
        results=results,
        digest_dir=output_cfg.get("digest_dir", "digests"),
        date_str=date_str,
        obsidian_dir=output_cfg.get("obsidian_dir"),
        keep_days=output_cfg.get("keep_days", 30),
    )
    log.info("done — %s", digest_path)


if __name__ == "__main__":
    main()
