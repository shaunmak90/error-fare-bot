"""
Error / Mistake Fare Alert Bot
--------------------------------
Checks a list of flight-deal RSS feeds for new posts, filters them by the
destinations you care about (and optionally only "error fare" language),
and sends you a Telegram message for each match.

Runs for free on a schedule via GitHub Actions (see .github/workflows/check_deals.yml).
State (which posts you've already seen) is kept in seen.json so you don't
get the same alert twice.
"""

import json
import os
from pathlib import Path

import feedparser
import requests

HERE = Path(__file__).parent
CONFIG_PATH = HERE / "config.json"
SEEN_PATH = HERE / "seen.json"

# Free RSS feeds from well-known flight-deal / error-fare spotting sites.
# Add or remove feeds here as you discover more.
FEEDS = [
    "https://www.secretflying.com/feed/",
    "https://www.theflightdeal.com/feed",
    "https://www.fly4free.com/feed/",
]

ERROR_FARE_SIGNALS = [
    "error fare",
    "mistake fare",
    "glitch",
    "pricing error",
    "price error",
    "fare error",
]


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return default
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2))


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    resp.raise_for_status()


def matches_destination(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text_low = text.lower()
    return any(kw.lower() in text_low for kw in keywords)


def looks_like_error_fare(text: str) -> bool:
    text_low = text.lower()
    return any(sig in text_low for sig in ERROR_FARE_SIGNALS)


def main() -> None:
    config = load_json(CONFIG_PATH, {})
    keywords = config.get("destinations", [])
    only_error_fares = config.get("only_error_fares", False)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit(
            "Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID environment variables."
        )

    seen = set(load_json(SEEN_PATH, []))
    new_seen = list(seen)
    sent = 0

    for feed_url in FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            uid = entry.get("id") or entry.get("link")
            if not uid or uid in seen:
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            combined = f"{title} {summary}"

            new_seen.append(uid)
            seen.add(uid)

            if only_error_fares and not looks_like_error_fare(combined):
                continue
            if not matches_destination(combined, keywords):
                continue

            message = f"\u2708\ufe0f {title}\n{link}"
            send_telegram(token, chat_id, message)
            sent += 1

    # Cap seen.json so it doesn't grow forever
    save_json(SEEN_PATH, new_seen[-3000:])
    print(f"Checked {len(FEEDS)} feeds, sent {sent} new alert(s).")


if __name__ == "__main__":
    main()
