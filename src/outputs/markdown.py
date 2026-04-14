"""Write digest summaries to dated Markdown files."""
from __future__ import annotations
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.processors.summarizer import SummaryResult

log = logging.getLogger(__name__)


def write_digest(
    results: list[SummaryResult],
    digest_dir: str,
    date_str: str,
    obsidian_dir: str | None = None,
    keep_days: int = 30,
) -> Path:
    out_dir = Path(digest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{date_str}-twitter-digest.md"
    out_path = out_dir / filename

    total_tweets = sum(r.tweet_count for r in results)
    lines = [
        f"# Twitter Digest — {date_str}",
        f"*{total_tweets} new tweets across {len(results)} topics*",
        "",
        "---",
        "",
    ]

    for result in results:
        lines.append(f"# {result.topic_label}")
        lines.append(f"*{result.tweet_count} tweets*")
        lines.append("")
        lines.append(result.summary)
        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote digest: %s", out_path)

    if obsidian_dir:
        obs_dir = Path(obsidian_dir).expanduser()
        obs_dir.mkdir(parents=True, exist_ok=True)
        obs_path = obs_dir / filename
        shutil.copy2(out_path, obs_path)
        log.info("copied to Obsidian: %s", obs_path)

    _prune_old_digests(out_dir, keep_days)
    return out_path


def _prune_old_digests(out_dir: Path, keep_days: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    for f in out_dir.glob("*-twitter-digest.md"):
        try:
            date_part = f.name[:10]  # YYYY-MM-DD
            file_date = datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date < cutoff:
                f.unlink()
                log.info("pruned old digest: %s", f.name)
        except ValueError:
            pass
