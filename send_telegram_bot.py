#!/usr/bin/env python3
"""
Send twitter-pull digest directly to Telegram using the bot API.
Reads bot token and chat ID from .env.telegram
"""
import os
import sys
import time
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
    # Manual env loading
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
        # Manual parse
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

# Get config from environment (required)
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


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text


def send_telegram_message(text: str, chat_id: str = TELEGRAM_CHAT_ID, bot_token: str = TELEGRAM_BOT_TOKEN) -> bool:
    """Send message to Telegram using bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Try with plain text first (more reliable)
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

    content = digest_path.read_text()

    # Add header (plain text, not markdown)
    header = f"🐦 Twitter Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"

    # Split into chunks
    chunks = format_for_telegram(content)

    # Send all chunks with rate limiting
    success = True
    for i, chunk in enumerate(chunks, 1):
        msg = (header + chunk) if i == 1 else chunk

        if i > 1:
            print(f"Sending chunk {i}/{len(chunks)}...")
            # Add delay to avoid rate limiting (Telegram allows ~30 msgs/second to groups, but be conservative)
            time.sleep(2)  # 2 second delay between messages

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
