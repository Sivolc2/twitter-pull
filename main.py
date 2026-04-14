#!/usr/bin/env python3
"""
twitter-pull — periodic Twitter/X digest generator

Usage:
  python main.py                        # run all topics
  python main.py --topics ai_updates    # run specific topics
  python main.py --accounts-only        # only pull account timelines
  python main.py --dry-run              # fetch but don't write output
"""
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


def load_config():
    cfg_dir = Path(__file__).parent / "config"

    with open(cfg_dir / "settings.yaml") as f:
        settings_raw = f.read()
    # expand env vars in settings
    for key, val in os.environ.items():
        settings_raw = settings_raw.replace(f"${{{key}}}", val)
    settings = yaml.safe_load(settings_raw)

    with open(cfg_dir / "topics.yaml") as f:
        topics = yaml.safe_load(f)

    # allow local overrides (gitignored)
    local_path = cfg_dir / "settings.local.yaml"
    if local_path.exists():
        with open(local_path) as f:
            local_raw = f.read()
        for key, val in os.environ.items():
            local_raw = local_raw.replace(f"${{{key}}}", val)
        local = yaml.safe_load(local_raw)
        _deep_merge(settings, local)

    return settings, topics


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def build_fetcher(settings: dict):
    backend = settings.get("fetcher", "twitterapi_io")
    if backend == "twitterapi_io":
        from src.fetchers.twitterapi_io import TwitterAPIioFetcher
        cfg = settings["twitterapi_io"]
        return TwitterAPIioFetcher(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            rate_limit_pause=cfg.get("rate_limit_pause", 1.0),
        )
    elif backend == "getxapi":
        from src.fetchers.getxapi import GetXAPIFetcher
        cfg = settings["getxapi"]
        return GetXAPIFetcher(
            api_key=cfg["api_key"],
            rate_limit_pause=cfg.get("rate_limit_pause", 1.0),
        )
    elif backend == "twscrape":
        from src.fetchers.twscrape_fetcher import TwscrapeFetcher
        cfg = settings["twscrape"]
        return TwscrapeFetcher(accounts_db=cfg["accounts_db"])
    else:
        raise ValueError(f"Unknown fetcher backend: {backend}")


def main():
    parser = argparse.ArgumentParser(description="Twitter/X digest generator")
    parser.add_argument("--topics", nargs="*", help="specific topic keys to run (default: all)")
    parser.add_argument("--accounts-only", action="store_true", help="only pull account timelines")
    parser.add_argument("--topics-only", action="store_true", help="only run keyword topics")
    parser.add_argument("--dry-run", action="store_true", help="fetch but skip writing output")
    args = parser.parse_args()

    settings, topics_cfg = load_config()
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

    # ── keyword topic searches ──────────────────────────────────────────────
    if not args.accounts_only:
        topic_filter = set(args.topics) if args.topics else None
        for topic_key, topic_cfg in topics_cfg.get("topics", {}).items():
            if topic_filter and topic_key not in topic_filter:
                continue
            label = topic_cfg["label"]
            log.info("fetching topic: %s", label)
            all_tweets = []
            for query in topic_cfg["queries"]:
                tweets = fetcher.search(query, max_results=topic_cfg.get("max_results", 50))
                log.info("  query '%s': %d tweets", query[:60], len(tweets))
                all_tweets.extend(tweets)

            new_tweets = dedup.filter_new(all_tweets)
            log.info("topic %s: %d new tweets after dedup", label, len(new_tweets))
            result = summarizer.summarize(new_tweets, label, date_str)
            results.append(result)

    # ── account timelines ───────────────────────────────────────────────────
    if not args.topics_only:
        accounts_cfg = topics_cfg.get("accounts", {})
        key_people = accounts_cfg.get("key_people", [])
        max_per = accounts_cfg.get("max_results_per_account", 20)

        if key_people:
            log.info("fetching %d account timelines", len(key_people))
            all_account_tweets = []
            for entry in key_people:
                username = entry["username"]
                tweets = fetcher.timeline(username, max_results=max_per)
                log.info("  @%s: %d tweets", username, len(tweets))
                all_account_tweets.extend(tweets)

            new_account_tweets = dedup.filter_new(all_account_tweets)
            log.info("accounts: %d new tweets after dedup", len(new_account_tweets))
            result = summarizer.summarize(new_account_tweets, "Key People", date_str)
            results.append(result)

    fetcher.close()
    dedup.close()

    if not results:
        log.info("no results to write")
        return

    if args.dry_run:
        log.info("dry-run: skipping output write")
        for r in results:
            print(f"\n{'='*60}\n{r.topic_label} ({r.tweet_count} tweets)\n{r.summary}")
        return

    output_cfg = topics_cfg.get("output", {})
    digest_path = write_digest(
        results=results,
        digest_dir=output_cfg.get("digest_dir", "digests"),
        date_str=date_str,
        obsidian_dir=output_cfg.get("obsidian_dir"),
        keep_days=output_cfg.get("keep_days", 30),
    )
    log.info("done — digest at %s", digest_path)


if __name__ == "__main__":
    main()
