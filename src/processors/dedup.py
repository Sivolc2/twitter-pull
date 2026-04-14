"""SQLite-backed deduplication. Tracks tweet IDs seen within a rolling window."""
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.fetchers.base import Tweet

log = logging.getLogger(__name__)


class Deduplicator:
    def __init__(self, db_path: str, window_days: int = 7):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._window = timedelta(days=window_days)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_ids (
                tweet_id TEXT PRIMARY KEY,
                seen_at  TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def filter_new(self, tweets: list[Tweet]) -> list[Tweet]:
        """Return only tweets not seen in the dedup window. Marks them as seen."""
        cutoff = (datetime.now(timezone.utc) - self._window).isoformat()
        # purge old entries
        self._conn.execute("DELETE FROM seen_ids WHERE seen_at < ?", (cutoff,))
        self._conn.commit()

        ids = [t.id for t in tweets]
        if not ids:
            return []

        placeholders = ",".join("?" * len(ids))
        seen = {
            row[0]
            for row in self._conn.execute(
                f"SELECT tweet_id FROM seen_ids WHERE tweet_id IN ({placeholders})", ids
            )
        }

        new_tweets = [t for t in tweets if t.id not in seen]

        now = datetime.now(timezone.utc).isoformat()
        self._conn.executemany(
            "INSERT OR IGNORE INTO seen_ids (tweet_id, seen_at) VALUES (?, ?)",
            [(t.id, now) for t in new_tweets],
        )
        self._conn.commit()
        log.info("dedup: %d new / %d duplicates", len(new_tweets), len(tweets) - len(new_tweets))
        return new_tweets

    def close(self) -> None:
        self._conn.close()
