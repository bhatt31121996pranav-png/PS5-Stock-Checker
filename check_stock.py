"""
PS5 Stock Checker
Checks configured product pages for stock status and sends a Telegram
alert the moment a product flips from OUT OF STOCK -> IN STOCK.

State (last known status per product) is stored in state.json so we
only notify on a *change*, not on every run.
"""

import json
import os
import sys
import time
import requests
from bs4 import BeautifulSoup

STATE_FILE = "state.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Real-browser-like headers to reduce bot-detection blocks.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ---------------------------------------------------------------------
# Add every product you want tracked here.
# "type" determines which parser function is used below.
# ---------------------------------------------------------------------
PRODUCTS = [
    {
        "name": "PS5 825GB - Flipkart",
        "url": "https://dl.flipkart.com/dl/sony-playstation-5-console-825-gb/p/itma828c9032dd29?pid=GMCGHMTYZ8BUBMFB&lid=LSTGMCGHMTYZ8BUBMFBE2W9DE",
        "type": "flipkart",
    },
    # Example placeholders - replace/add real URLs:
    # {
    #     "name": "PS5 - Amazon",
    #     "url": "https://www.amazon.in/dp/XXXXXXXXXX",
    #     "type": "amazon",
    # },
    # {
    #     "name": "PS5 - Croma",
    #     "url": "https://www.croma.com/xxxxx/p/xxxxx",
    #     "type": "croma",
    # },
]


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing - skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"Telegram send failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Telegram send error: {e}")


def fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"  Non-200 status ({resp.status_code}) for {url}")
            return None
        return resp.text
    except Exception as e:
        print(f"  Fetch error for {url}: {e}")
        return None


def check_flipkart(html: str) -> str:
    """
    Returns 'IN_STOCK', 'OUT_OF_STOCK', or 'UNKNOWN'.
    Flipkart shows a "Notify Me" button when sold out, and
    "ADD TO CART" / "BUY NOW" when available.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).upper()

    if "NOTIFY ME" in text:
        return "OUT_OF_STOCK"
    if "ADD TO CART" in text or "BUY NOW" in text:
        return "IN_STOCK"
    return "UNKNOWN"


def check_amazon(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).upper()

    if "CURRENTLY UNAVAILABLE" in text or "OUT OF STOCK" in text:
        return "OUT_OF_STOCK"
    if "ADD TO CART" in text or "BUY NOW" in text:
        return "IN_STOCK"
    return "UNKNOWN"


def check_croma(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).upper()

    if "NOTIFY ME" in text or "SOLD OUT" in text or "OUT OF STOCK" in text:
        return "OUT_OF_STOCK"
    if "ADD TO CART" in text:
        return "IN_STOCK"
    return "UNKNOWN"


CHECKERS = {
    "flipkart": check_flipkart,
    "amazon": check_amazon,
    "croma": check_croma,
}


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    state = load_state()
    changed = False

    for product in PRODUCTS:
        name = product["name"]
        url = product["url"]
        ptype = product["type"]
        checker = CHECKERS.get(ptype)

        print(f"Checking: {name}")

        if checker is None:
            print(f"  Unknown type '{ptype}', skipping.")
            continue

        html = fetch_html(url)
        if html is None:
            print("  Could not fetch page (possibly blocked). Skipping this run.")
            continue

        status = checker(html)
        prev_status = state.get(name, {}).get("status", "UNKNOWN")

        print(f"  Previous: {prev_status} | Current: {status}")

        if status == "UNKNOWN":
            # Site structure may have changed, or page didn't load fully.
            # Don't overwrite previous known state; just log it.
            print("  Could not determine stock status confidently.")
        else:
            if status == "IN_STOCK" and prev_status != "IN_STOCK":
                msg = f"🎮 IN STOCK! {name}\n{url}\n\nGo grab it now!"
                print(f"  >>> Sending alert: {msg}")
                send_telegram(msg)

            state[name] = {"status": status, "url": url}
            changed = True

        time.sleep(2)  # polite delay between requests

    if changed:
        save_state(state)
    print("Done.")


if __name__ == "__main__":
    main()
