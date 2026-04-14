"""
TwitterAPI.io fetcher — $0.15 per 1,000 tweets.
Docs: https://twitterapi.io/docs
"""
from __future__ import annotations
import time
import logging
from datetime import datetime, timezone

import httpx

from .base import BaseFetcher, Tweet

log = logging.getLogger(__name__)


def _parse_tweet(raw: dict, topic: str | None = None, source_account: str | None = None) -> Tweet:
    author = raw.get("author", {})
    created_raw = raw.get("createdAt", "")
    try:
        created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        created_at = datetime.now(timezone.utc)

    tweet_id = str(raw.get("id", raw.get("id_str", "")))
    username = author.get("userName", author.get("screen_name", "unknown"))
    return Tweet(
        id=tweet_id,
        text=raw.get("text", raw.get("full_text", "")),
        author_username=username,
        author_name=author.get("name", username),
        created_at=created_at,
        like_count=raw.get("likeCount", raw.get("favorite_count", 0)),
        retweet_count=raw.get("retweetCount", raw.get("retweet_count", 0)),
        reply_count=raw.get("replyCount", raw.get("reply_count", 0)),
        url=f"https://x.com/{username}/status/{tweet_id}",
        is_retweet=bool(raw.get("isRetweet", raw.get("retweeted_status"))),
        topic=topic,
        source_account=source_account,
    )


class TwitterAPIioFetcher(BaseFetcher):
    def __init__(self, api_key: str, base_url: str, rate_limit_pause: float = 1.0):
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        self.base_url = base_url.rstrip("/")
        self.pause = rate_limit_pause
        self._client = httpx.Client(headers=self.headers, timeout=30)

    def search(self, query: str, max_results: int = 50) -> list[Tweet]:
        tweets: list[Tweet] = []
        cursor = None
        while len(tweets) < max_results:
            params: dict = {
                "query": query,
                "queryType": "Latest",
                "count": min(max_results - len(tweets), 20),
            }
            if cursor:
                params["cursor"] = cursor

            try:
                resp = self._client.get(f"{self.base_url}/tweet/advanced_search", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                log.error("search HTTP error %s: %s", e.response.status_code, e.response.text)
                break
            except Exception as e:
                log.error("search error: %s", e)
                break

            raw_tweets = data.get("tweets", [])
            for rt in raw_tweets:
                tweets.append(_parse_tweet(rt, topic=query))

            cursor = data.get("next_cursor")
            if not cursor or not raw_tweets:
                break
            time.sleep(self.pause)

        return tweets[:max_results]

    def timeline(self, username: str, max_results: int = 20) -> list[Tweet]:
        tweets: list[Tweet] = []
        cursor = None
        while len(tweets) < max_results:
            params: dict = {
                "userName": username,
                "count": min(max_results - len(tweets), 20),
            }
            if cursor:
                params["cursor"] = cursor

            try:
                resp = self._client.get(f"{self.base_url}/user/last_tweets", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                log.error("timeline HTTP error %s for @%s: %s", e.response.status_code, username, e.response.text)
                break
            except Exception as e:
                log.error("timeline error for @%s: %s", username, e)
                break

            raw_tweets = data.get("tweets", [])
            for rt in raw_tweets:
                tweets.append(_parse_tweet(rt, source_account=username))

            cursor = data.get("next_cursor")
            if not cursor or not raw_tweets:
                break
            time.sleep(self.pause)

        return tweets[:max_results]

    def close(self) -> None:
        self._client.close()
