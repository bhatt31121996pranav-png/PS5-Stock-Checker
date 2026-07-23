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
        "name": "PS5 825GB Disc - Flipkart",
        "url": "https://dl.flipkart.com/dl/sony-playstation-5-console-825-gb/p/itma828c9032dd29?pid=GMCGHMTYZ8BUBMFB&lid=LSTGMCGHMTYZ8BUBMFBE2W9DE",
        "type": "flipkart",
    },
    {
        "name": "PS5 Disc - Amazon",
        "url": "https://www.amazon.in/Sony-CFI-2008A01X-PlayStation5-Console-slim/dp/B0CY5HVDS2",
        "type": "amazon",
    },
    {
        "name": "PS5 Digital - Amazon",
        "url": "https://www.amazon.in/Sony-PlayStation%C2%AE5-Digital-Edition-slim/dp/B0CY5QW186",
        "type": "amazon",
    },
    {
        "name": "PS5 Disc - Croma",
        "url": "https://www.croma.com/sony-playstation-5-slim-1tb-ssd-gaming-console-white-/p/305985",
        "type": "croma",
    },
    {
        "name": "PS5 Digital - Croma",
        "url": "https://www.croma.com/sony-ps5-slim-digital-edition-console/p/305987",
        "type": "croma",
    },
    {
        "name": "PS5 Disc - Reliance Digital",
        "url": "https://www.reliancedigital.in/product/sony-playstation-ps5-slim-console-luh1rv-7537998",
        "type": "reliancedigital",
    },
    {
        "name": "PS5 Digital - Reliance Digital",
        "url": "https://www.reliancedigital.in/product/sony-playstation-ps5-slim-digital-console-luh1rv-7537999",
        "type": "reliancedigital",
    },
    {
        "name": "PS5 Disc - Sony Center",
        "url": "https://shopatsc.com/products/playstation-5-standard-edition",
        "type": "sonycenter",
    },
    {
        "name": "PS5 Digital - Sony Center",
        "url": "https://shopatsc.com/products/playstation-5-digital-edition",
        "type": "sonycenter",
    },
    {
        "name": "PS5 Disc - Vijay Sales",
        "url": "https://www.vijaysales.com/p/227607/sony-playstation-5-slim-disc-edition",
        "type": "vijaysales",
    },
    {
        "name": "PS5 Digital - Vijay Sales",
        "url": "https://www.vijaysales.com/p/247617/sony-playstationr5-digital-edition-with-ea-sports-fc-26-bundle-ps5-slim",
        "type": "vijaysales",
    },
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


def check_reliancedigital(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).upper()

    if "NOTIFY ME" in text or "OUT OF STOCK" in text or "CURRENTLY UNAVAILABLE" in text:
        return "OUT_OF_STOCK"
    if "ADD TO CART" in text:
        return "IN_STOCK"
    return "UNKNOWN"


def check_sonycenter(html: str) -> str:
    """Sony Center (shopatsc.com) - Shopify storefront. Shows 'Notify Me'
    when a store restock notification form appears (sold out)."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).upper()

    if "NOTIFY ME" in text or "OUT OF STOCK" in text or "SOLD OUT" in text:
        return "OUT_OF_STOCK"
    if "ADD TO CART" in text or "BUY NOW" in text:
        return "IN_STOCK"
    return "UNKNOWN"


def check_vijaysales(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).upper()

    if "NOTIFY" in text and "AVAILABLE" in text:
        # e.g. "you'll receive a notification ... when the product is available"
        return "OUT_OF_STOCK"
    if "OUT OF STOCK" in text or "SOLD OUT" in text:
        return "OUT_OF_STOCK"
    if "ADD TO CART" in text or "BUY NOW" in text:
        return "IN_STOCK"
    return "UNKNOWN"


CHECKERS = {
    "flipkart": check_flipkart,
    "amazon": check_amazon,
    "croma": check_croma,
    "reliancedigital": check_reliancedigital,
    "sonycenter": check_sonycenter,
    "vijaysales": check_vijaysales,
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
