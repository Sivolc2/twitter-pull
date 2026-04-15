#!/usr/bin/env python3
"""
Send condensed twitter-pull summary to Telegram.
Only includes AI-generated summaries, not full tweet text.
"""
import os
import sys
import time
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], check=True)
    import httpx

try:
    from dotenv import load_dotenv
except ImportError:
    pass

ROOT = Path(__file__).parent
DIGEST_DIR = ROOT / "digests"

# Load Telegram config
env_file = ROOT / ".env.telegram"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def get_latest_digest() -> Path | None:
    """Find the most recent digest markdown file."""
    if not DIGEST_DIR.exists():
        return None
    digests = list(DIGEST_DIR.glob("*.md"))
    if not digests:
        return None
    return max(digests, key=lambda p: p.stat().st_mtime)


def extract_summaries(content: str) -> str:
    """Extract only the AI-generated summaries from the digest, skipping individual tweets."""
    lines = content.split('\n')
    result = []
    in_summary_section = False
    in_top_tweets = False
    current_section = []

    for line in lines:
        # Main title
        if line.startswith('# Twitter Digest'):
            result.append(line)
            continue

        # Tweet count summary
        if line.startswith('*') and 'new tweets' in line and 'topics' in line:
            result.append(line)
            result.append('')
            continue

        # Topic headers (e.g., "# AI News")
        if line.startswith('# ') and not line.startswith('## '):
            result.append('---')
            result.append(line)
            in_summary_section = False
            in_top_tweets = False
            continue

        # Tweet count per topic
        if line.startswith('*') and 'tweets*' in line:
            result.append(line)
            continue

        # Skip "Top Tweets" sections (individual tweet listings)
        if line.startswith('## Top Tweets'):
            in_top_tweets = True
            continue

        # Summary sections
        if line.startswith('## ') and not line.startswith('## Top Tweets'):
            in_summary_section = True
            in_top_tweets = False
            result.append(line)
            continue

        # Skip individual tweet listings
        if in_top_tweets:
            # Skip until we hit a new section
            if line.startswith('#'):
                in_top_tweets = False
            else:
                continue

        # Include summary content
        if in_summary_section:
            result.append(line)
        elif line == '---' or line == '*(no new tweets)*':
            result.append(line)

    return '\n'.join(result).strip()


def send_telegram_message(text: str, chat_id: str = TELEGRAM_CHAT_ID, bot_token: str = TELEGRAM_BOT_TOKEN) -> bool:
    """Send message to Telegram using bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    try:
        resp = httpx.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        print(f"✓ Sent to Telegram chat {chat_id}")
        return True
    except httpx.HTTPStatusError as e:
        print(f"✗ Telegram API error {e.response.status_code}: {e.response.text[:300]}")
        return False
    except Exception as e:
        print(f"✗ Error sending to Telegram: {e}")
        return False


def format_for_telegram(content: str, max_length: int = 4000) -> list[str]:
    """Split content into Telegram-friendly chunks (max 4096 chars)."""
    if len(content) <= max_length:
        return [content]

    chunks = []
    lines = content.split('\n')
    current_chunk = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1
        if current_length + line_length > max_length:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length

    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks


def main():
    digest_path = get_latest_digest()
    if not digest_path:
        print("No digest found")
        return 1

    print(f"Found digest: {digest_path}")

    # Read and extract summaries only
    content = digest_path.read_text()
    summary = extract_summaries(content)

    # Add header
    header = f"🐦 Twitter Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"

    # Split into chunks
    chunks = format_for_telegram(summary)
    print(f"Sending {len(chunks)} message(s)...")

    # Send all chunks with rate limiting
    success = True
    for i, chunk in enumerate(chunks, 1):
        msg = (header + chunk) if i == 1 else chunk

        if i > 1:
            print(f"Sending chunk {i}/{len(chunks)}...")
            time.sleep(2)  # Rate limiting

        if not send_telegram_message(msg):
            success = False
            break

    if success:
        print(f"✓ Successfully sent {len(chunks)} message(s) to Telegram")
        return 0
    else:
        print(f"✗ Failed to send digest")
        return 1


if __name__ == "__main__":
    sys.exit(main())
