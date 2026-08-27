"""
Route Price Scorer
-------------------
For each origin/destination route you configure, this checks Travelpayouts'
"special offers" endpoint (which specifically flags abnormally low prices)
and cross-references it against a baseline average price for that route to
compute a savings percentage and a 0-100 "deal score".

Sends a Telegram alert for any route currently showing a strong deal.

Requires a free Travelpayouts token (see README.md for signup steps).
"""

import json
import os
from pathlib import Path

import requests

HERE = Path(__file__).parent
CONFIG_PATH = HERE / "config.json"
ROUTE_SEEN_PATH = HERE / "route_seen.json"

SPECIAL_OFFERS_URL = "https://api.travelpayouts.com/aviasales/v3/get_special_offers"
CALENDAR_URL = "https://api.travelpayouts.com/v2/prices/week-matrix"

# Minimum % below baseline to bother alerting on
MIN_SAVINGS_PERCENT = 40


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
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
        timeout=15,
    )
    resp.raise_for_status()


def get_baseline_price(tp_token: str, origin: str, destination: str) -> float | None:
    """Average of cheapest prices across the coming weeks for this route."""
    params = {
        "currency": "usd",
        "origin": origin,
        "destination": destination,
        "show_to_affiliates": "true",
        "token": tp_token,
    }
    resp = requests.get(CALENDAR_URL, params=params, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json().get("data", {})

    # Travelpayouts has returned this endpoint's "data" as either a dict
    # keyed by date, or a plain list of entries, depending on the route/
    # response version. Handle both so this doesn't break either way.
    if isinstance(data, dict):
        entries = data.values()
    elif isinstance(data, list):
        entries = data
    else:
        entries = []

    prices = [e["price"] for e in entries if isinstance(e, dict) and "price" in e]
    if not prices:
        return None
    return sum(prices) / len(prices)


def get_special_offers(tp_token: str, origin: str, destination: str) -> list[dict]:
    params = {
        "origin": origin,
        "destination": destination,
        "locale": "en",
        "token": tp_token,
    }
    resp = requests.get(SPECIAL_OFFERS_URL, params=params, timeout=15)
    if resp.status_code != 200:
        return []
    return resp.json().get("data", [])


def score_offer(price: float, baseline: float) -> tuple[float, float]:
    """Returns (savings_percent, score_0_to_100)."""
    if baseline <= 0:
        return 0.0, 0.0
    savings_percent = max(0.0, (1 - price / baseline) * 100)
    # simple score: savings percent capped at 100
    score = min(100.0, savings_percent)
    return round(savings_percent, 1), round(score, 1)


def main() -> None:
    config = load_json(CONFIG_PATH, {})
    routes = config.get("routes", [])
    min_savings = config.get("min_savings_percent", MIN_SAVINGS_PERCENT)

    tp_token = os.environ.get("TRAVELPAYOUTS_TOKEN")
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not tp_token or not tg_token or not chat_id:
        raise SystemExit(
            "Missing TRAVELPAYOUTS_TOKEN / TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID env vars."
        )

    if not routes:
        print("No routes configured in config.json — nothing to check.")
        return

    seen = load_json(ROUTE_SEEN_PATH, [])
    seen_set = set(seen)
    new_seen = list(seen)
    sent = 0

    for route in routes:
        origin = route.get("origin", "").upper()
        destination = route.get("destination", "").upper()
        if not origin or not destination:
            continue

        baseline = get_baseline_price(tp_token, origin, destination)
        if baseline is None:
            continue

        offers = get_special_offers(tp_token, origin, destination)
        for offer in offers:
            price = offer.get("price")
            departure_at = offer.get("departure_at", "")
            link = offer.get("link", "")
            uid = f"{origin}-{destination}-{departure_at}-{price}"
            if price is None or uid in seen_set:
                continue

            new_seen.append(uid)
            seen_set.add(uid)

            savings_percent, score = score_offer(price, baseline)
            if savings_percent < min_savings:
                continue

            message = (
                f"\U0001f6a8 Deal score {score}/100\n"
                f"{origin} \u2192 {destination}\n"
                f"Price: ${price} (baseline ~${round(baseline)})\n"
                f"Savings: {savings_percent}% below average\n"
                f"Departs: {departure_at}\n"
                f"https://www.aviasales.com{link}" if link else ""
            )
            send_telegram(tg_token, chat_id, message)
            sent += 1

    save_json(ROUTE_SEEN_PATH, new_seen[-3000:])
    print(f"Checked {len(routes)} route(s), sent {sent} scored alert(s).")


if __name__ == "__main__":
    main()
