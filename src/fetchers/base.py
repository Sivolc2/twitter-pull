from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Tweet:
    id: str
    text: str
    author_username: str
    author_name: str
    created_at: datetime
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    url: str = ""
    is_retweet: bool = False
    topic: Optional[str] = None        # which topic/query produced this
    source_account: Optional[str] = None  # if from timeline pull

    def engagement_score(self) -> int:
        return self.like_count + self.retweet_count * 2 + self.reply_count


class BaseFetcher(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 50) -> list[Tweet]:
        """Search tweets by query string."""

    @abstractmethod
    def timeline(self, username: str, max_results: int = 20) -> list[Tweet]:
        """Pull recent tweets from a user's timeline."""

    @abstractmethod
    def close(self) -> None:
        """Clean up any connections or sessions."""
