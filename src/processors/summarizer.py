"""
Claude-powered summarization of tweet batches into human-readable digests.
Falls back to a simple text join if no API key is set.
"""
import logging
import textwrap
from dataclasses import dataclass

from src.fetchers.base import Tweet

log = logging.getLogger(__name__)

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert analyst distilling social media signals into concise, actionable briefings.
    You receive a batch of tweets on a specific topic and produce a structured digest.
    Be specific — name models, companies, people, and numbers. Cut filler.
    Preserve tweet URLs as sources where relevant.
""")

USER_PROMPT_TEMPLATE = textwrap.dedent("""\
    Topic: {topic_label}
    Tweets collected: {count}
    Date: {date}

    ---
    {tweet_block}
    ---

    Write a digest with these sections:
    ## Key Themes
    (3-5 bullet points on the main narratives)

    ## Notable Signals
    (specific launches, papers, tools, quotes worth noting — with source URLs)

    ## People to Watch
    (who was most insightful or active on this topic today)

    ## One-Line Summary
    (single sentence capturing the most important thing)
""")


@dataclass
class SummaryResult:
    topic_label: str
    summary: str
    tweet_count: int


def _format_tweet(t: Tweet) -> str:
    return (
        f"@{t.author_username} ({t.like_count}♥ {t.retweet_count}🔁): {t.text}\n"
        f"  {t.url}"
    )


def _simple_summary(tweets: list[Tweet], topic_label: str) -> str:
    """Fallback: just list the top tweets by engagement."""
    sorted_tweets = sorted(tweets, key=lambda t: t.engagement_score(), reverse=True)
    lines = [f"## Top Tweets — {topic_label}\n"]
    for t in sorted_tweets[:20]:
        lines.append(_format_tweet(t))
        lines.append("")
    return "\n".join(lines)


class Summarizer:
    def __init__(self, provider: str, model: str, api_key: str, max_tokens: int, batch_size: int):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.batch_size = batch_size
        self._client = None

        if provider == "anthropic" and api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                log.warning("anthropic package not installed; falling back to plain summary")
        elif provider == "openai" and api_key:
            try:
                import openai
                self._client = openai.OpenAI(api_key=api_key)
            except ImportError:
                log.warning("openai package not installed; falling back to plain summary")

    def summarize(self, tweets: list[Tweet], topic_label: str, date_str: str) -> SummaryResult:
        if not tweets:
            return SummaryResult(topic_label=topic_label, summary="*(no new tweets)*", tweet_count=0)

        # sort by engagement, take top batch_size
        ranked = sorted(tweets, key=lambda t: t.engagement_score(), reverse=True)[:self.batch_size]
        tweet_block = "\n\n".join(_format_tweet(t) for t in ranked)

        if self._client is None:
            return SummaryResult(
                topic_label=topic_label,
                summary=_simple_summary(tweets, topic_label),
                tweet_count=len(tweets),
            )

        prompt = USER_PROMPT_TEMPLATE.format(
            topic_label=topic_label,
            count=len(tweets),
            date=date_str,
            tweet_block=tweet_block,
        )

        try:
            if self.provider == "anthropic":
                msg = self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                summary = msg.content[0].text
            elif self.provider == "openai":
                resp = self._client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                summary = resp.choices[0].message.content
            else:
                summary = _simple_summary(tweets, topic_label)
        except Exception as e:
            log.error("summarization API error: %s", e)
            summary = _simple_summary(tweets, topic_label)

        return SummaryResult(topic_label=topic_label, summary=summary, tweet_count=len(tweets))
