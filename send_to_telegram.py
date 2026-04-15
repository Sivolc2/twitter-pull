#!/usr/bin/env python3
"""
Send twitter-pull digest to user via OpenClaw Telegram bot.
This script runs after main.py to deliver the digest.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], check=True)
    import httpx

ROOT = Path(__file__).parent
DIGEST_DIR = ROOT / "digests"

# OpenClaw API configuration
OPENCLAW_BASE_URL = os.environ.get("OPENCLAW_BASE_URL", "http://localhost:18789")
OPENCLAW_TOKEN = os.environ.get("OPENCLAW_TOKEN", "")  # Optional - some installs don't require auth
OPENCLAW_SESSION = os.environ.get("OPENCLAW_SESSION", "main")


def get_latest_digest() -> Path | None:
    """Find the most recent digest markdown file."""
    if not DIGEST_DIR.exists():
        return None

    digests = list(DIGEST_DIR.glob("*.md"))
    if not digests:
        return None

    # Sort by modification time, return most recent
    return max(digests, key=lambda p: p.stat().st_mtime)


def send_via_http_api(content: str, session: str = OPENCLAW_SESSION) -> bool:
    """Send message via OpenClaw HTTP API."""
    url = f"{OPENCLAW_BASE_URL.rstrip('/')}/api/sessions/{session}/messages"

    headers = {"Content-Type": "application/json"}
    if OPENCLAW_TOKEN:
        headers["Authorization"] = f"Bearer {OPENCLAW_TOKEN}"

    payload = {
        "role": "user",
        "content": content
    }

    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=30.0)
        resp.raise_for_status()
        print(f"✓ Sent to OpenClaw session '{session}'")
        return True
    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP error {e.response.status_code}: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"✗ Error sending to OpenClaw: {e}")
        return False


def send_via_cli_fallback(content: str, recipient: str | None = None) -> bool:
    """Fallback: Send via openclaw CLI."""
    import subprocess

    cmd = ["openclaw", "agent", "--deliver", "--channel", "telegram", "--message", content]

    if recipient:
        cmd.extend(["--to", recipient])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✓ Sent via OpenClaw CLI")
            return True
        else:
            print(f"✗ CLI failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"✗ CLI error: {e}")
        return False


def format_for_telegram(content: str, max_length: int = 4000) -> list[str]:
    """
    Split content into Telegram-friendly chunks.
    Telegram has a 4096 character limit per message.
    """
    if len(content) <= max_length:
        return [content]

    chunks = []
    lines = content.split('\n')
    current_chunk = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1  # +1 for newline
        if current_length + line_length > max_length:
            # Save current chunk and start new one
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length

    # Add remaining chunk
    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    return chunks


def main():
    # Get configuration from environment
    recipient = os.environ.get("TELEGRAM_RECIPIENT")
    use_http = os.environ.get("OPENCLAW_USE_HTTP", "true").lower() == "true"

    # Find latest digest
    digest_path = get_latest_digest()
    if not digest_path:
        print("No digest found")
        return 1

    print(f"Found digest: {digest_path}")

    # Read digest content
    content = digest_path.read_text()

    # Format header
    header = f"🐦 Twitter Digest - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"

    # Split into chunks if needed
    chunks = format_for_telegram(content)

    # Send chunks
    success = True
    for i, chunk in enumerate(chunks, 1):
        # Add header to first chunk
        msg = (header + chunk) if i == 1 else chunk

        if i > 1:
            print(f"Sending chunk {i}/{len(chunks)}...")

        # Try HTTP API first, fall back to CLI
        if use_http:
            if not send_via_http_api(msg):
                print("Trying CLI fallback...")
                if not send_via_cli_fallback(msg, recipient):
                    success = False
                    break
        else:
            if not send_via_cli_fallback(msg, recipient):
                success = False
                break

    if success:
        print(f"✓ Successfully sent {len(chunks)} message(s)")
        return 0
    else:
        print(f"✗ Failed to send digest")
        return 1


if __name__ == "__main__":
    sys.exit(main())
