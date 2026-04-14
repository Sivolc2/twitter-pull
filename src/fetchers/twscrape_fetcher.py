"""
twscrape fetcher — free but fragile (uses Twitter's internal GraphQL API).
Requires real Twitter accounts added via: twscrape add_accounts accounts.txt

Accounts file format (one per line):
  username:password:email:email_password

Install: pip install twscrape
"""
import asyncio
import logging
from datetime import timezone

from .base import BaseFetcher, Tweet

log = logging.getLogger(__name__)


def _require_twscrape():
    try:
        import twscrape
        return twscrape
    except ImportError:
        raise ImportError("twscrape not installed. Run: pip install twscrape")


def _to_tweet(tw, topic=None, source_account=None) -> Tweet:
    username = tw.user.username if tw.user else "unknown"
    return Tweet(
        id=str(tw.id),
        text=tw.rawContent,
        author_username=username,
        author_name=tw.user.displayname if tw.user else username,
        created_at=tw.date.replace(tzinfo=timezone.utc) if tw.date.tzinfo is None else tw.date,
        like_count=tw.likeCount or 0,
        retweet_count=tw.retweetCount or 0,
        reply_count=tw.replyCount or 0,
        url=tw.url,
        is_retweet=tw.retweetedTweet is not None,
        topic=topic,
        source_account=source_account,
    )


class TwscrapeFetcher(BaseFetcher):
    def __init__(self, accounts_db: str):
        twscrape = _require_twscrape()
        self._api = twscrape.API(accounts_db)
        self._loop = asyncio.new_event_loop()

    def search(self, query: str, max_results: int = 50) -> list[Tweet]:
        async def _run():
            tweets = []
            async for tw in self._api.search(query, limit=max_results):
                tweets.append(_to_tweet(tw, topic=query))
            return tweets
        try:
            return self._loop.run_until_complete(_run())
        except Exception as e:
            log.error("twscrape search error: %s", e)
            return []

    def timeline(self, username: str, max_results: int = 20) -> list[Tweet]:
        async def _run():
            user = await self._api.user_by_login(username)
            if not user:
                log.warning("twscrape: user not found: @%s", username)
                return []
            tweets = []
            async for tw in self._api.user_tweets(user.id, limit=max_results):
                tweets.append(_to_tweet(tw, source_account=username))
            return tweets
        try:
            return self._loop.run_until_complete(_run())
        except Exception as e:
            log.error("twscrape timeline error for @%s: %s", username, e)
            return []

    def close(self) -> None:
        self._loop.close()
