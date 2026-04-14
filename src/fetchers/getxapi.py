"""
GetXAPI fetcher — $0.05 per 1,000 tweets (~3× cheaper than TwitterAPI.io).
Sign up at https://getxapi.com — free $0.10 credit on signup (~2,000 tweets).
Docs: https://docs.getxapi.com

Endpoints:
  Search:   GET /twitter/tweet/advanced_search?q=...&product=Latest
  Timeline: GET /twitter/user/tweets?userName=...
"""
from __future__ import annotations
import time
import logging
from datetime import datetime, timezone

import httpx

from .base import BaseFetcher, Tweet

log = logging.getLogger(__name__)

BASE_URL = "https://api.getxapi.com"


def _parse_tweet(raw: dict, topic: str | None = None, source_account: str | None = None) -> Tweet:
    author = raw.get("author", {})
    created_raw = raw.get("createdAt", "")
    try:
        created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        created_at = datetime.now(timezone.utc)

    tweet_id = str(raw.get("id", ""))
    username = author.get("userName", "unknown")
    url = raw.get("twitterUrl", raw.get("url", f"https://x.com/{username}/status/{tweet_id}"))

    return Tweet(
        id=tweet_id,
        text=raw.get("text", ""),
        author_username=username,
        author_name=author.get("name", username),
        created_at=created_at,
        like_count=raw.get("likeCount", 0),
        retweet_count=raw.get("retweetCount", 0),
        reply_count=raw.get("replyCount", 0),
        url=url,
        is_retweet=raw.get("type") == "retweet",
        topic=topic,
        source_account=source_account,
    )


class GetXAPIFetcher(BaseFetcher):
    def __init__(self, api_key: str, rate_limit_pause: float = 1.0):
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.pause = rate_limit_pause
        self._client = httpx.Client(headers=self.headers, timeout=30)

    def search(self, query: str, max_results: int = 50) -> list[Tweet]:
        tweets: list[Tweet] = []
        cursor = None
        while len(tweets) < max_results:
            params: dict = {
                "q": query,
                "product": "Latest",
            }
            if cursor:
                params["cursor"] = cursor

            try:
                resp = self._client.get(f"{BASE_URL}/twitter/tweet/advanced_search", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                log.error("GetXAPI search error %s: %s", e.response.status_code, e.response.text[:200])
                break
            except Exception as e:
                log.error("GetXAPI search error: %s", e)
                break

            for raw in data.get("tweets", []):
                tweets.append(_parse_tweet(raw, topic=query))

            if not data.get("has_more") or not data.get("next_cursor"):
                break
            cursor = data["next_cursor"]
            time.sleep(self.pause)

        return tweets[:max_results]

    def timeline(self, username: str, max_results: int = 20) -> list[Tweet]:
        tweets: list[Tweet] = []
        cursor = None
        while len(tweets) < max_results:
            params: dict = {"userName": username}
            if cursor:
                params["cursor"] = cursor

            try:
                resp = self._client.get(f"{BASE_URL}/twitter/user/tweets", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                log.error("GetXAPI timeline error %s for @%s: %s", e.response.status_code, username, e.response.text[:200])
                break
            except Exception as e:
                log.error("GetXAPI timeline error for @%s: %s", username, e)
                break

            for raw in data.get("tweets", []):
                tweets.append(_parse_tweet(raw, source_account=username))

            if not data.get("has_more") or not data.get("next_cursor") or len(tweets) >= max_results:
                break
            cursor = data["next_cursor"]
            time.sleep(self.pause)

        return tweets[:max_results]

    def close(self) -> None:
        self._client.close()
