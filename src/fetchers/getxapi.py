"""
GetXAPI fetcher — $0.05 per 1,000 tweets (~3× cheaper than TwitterAPI.io).
Sign up at https://getxapi.com — free $0.10 credit on signup (~2,000 tweets).
Docs: https://getxapi.com/docs
"""
from __future__ import annotations
import time
import logging
from datetime import datetime, timezone

import httpx

from .base import BaseFetcher, Tweet

log = logging.getLogger(__name__)

BASE_URL = "https://api.getxapi.com/v2"


def _parse_tweet(raw: dict, topic: str | None = None, source_account: str | None = None) -> Tweet:
    author = raw.get("user", raw.get("author", {}))
    created_raw = raw.get("created_at", raw.get("createdAt", ""))
    try:
        created_at = datetime.strptime(created_raw, "%a %b %d %H:%M:%S +0000 %Y").replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        try:
            created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = datetime.now(timezone.utc)

    tweet_id = str(raw.get("id_str", raw.get("id", "")))
    username = author.get("screen_name", author.get("userName", "unknown"))
    return Tweet(
        id=tweet_id,
        text=raw.get("full_text", raw.get("text", "")),
        author_username=username,
        author_name=author.get("name", username),
        created_at=created_at,
        like_count=raw.get("favorite_count", raw.get("likeCount", 0)),
        retweet_count=raw.get("retweet_count", raw.get("retweetCount", 0)),
        reply_count=raw.get("reply_count", raw.get("replyCount", 0)),
        url=f"https://x.com/{username}/status/{tweet_id}",
        is_retweet="retweeted_status" in raw or raw.get("isRetweet", False),
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
                "query": query,
                "count": min(max_results - len(tweets), 20),
                "result_type": "recent",
            }
            if cursor:
                params["cursor"] = cursor

            try:
                resp = self._client.get(f"{BASE_URL}/search/tweets", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                log.error("GetXAPI search error %s: %s", e.response.status_code, e.response.text)
                break
            except Exception as e:
                log.error("GetXAPI search error: %s", e)
                break

            statuses = data.get("statuses", data.get("tweets", []))
            for raw in statuses:
                tweets.append(_parse_tweet(raw, topic=query))

            cursor = data.get("next_cursor") or data.get("search_metadata", {}).get("next_results")
            if not cursor or not statuses:
                break
            time.sleep(self.pause)

        return tweets[:max_results]

    def timeline(self, username: str, max_results: int = 20) -> list[Tweet]:
        tweets: list[Tweet] = []
        params: dict = {
            "screen_name": username,
            "count": min(max_results, 200),
            "tweet_mode": "extended",
            "exclude_replies": False,
            "include_rts": False,
        }

        try:
            resp = self._client.get(f"{BASE_URL}/statuses/user_timeline", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            log.error("GetXAPI timeline error %s for @%s: %s", e.response.status_code, username, e.response.text)
            return []
        except Exception as e:
            log.error("GetXAPI timeline error for @%s: %s", username, e)
            return []

        raw_list = data if isinstance(data, list) else data.get("tweets", [])
        for raw in raw_list[:max_results]:
            tweets.append(_parse_tweet(raw, source_account=username))

        return tweets

    def close(self) -> None:
        self._client.close()
