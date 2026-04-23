"""
Debug script — parses a Sephora order detail page and prints what the
delivery scraper would extract.

Usage (from repo root):

  From a saved HTML file (recommended — no auth needed):
    python backend/scripts/debug_sephora_delivery.py --file backend/scripts/order.html

  From a live URL (requires valid SEPHORA_STORAGE_STATE):
    python backend/scripts/debug_sephora_delivery.py --url https://www.sephora.com/profile/orderdetail/12345
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs4 import BeautifulSoup
from app.scrapers.sephora import parse_sephora_delivery_html

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--file", help="Path to saved HTML file")
group.add_argument("--url", help="Live Sephora order URL")
args = parser.parse_args()

if args.file:
    html = Path(args.file).read_text(encoding="utf-8")
    print(f"\nParsing file: {args.file}")
else:
    from app.scrapers.playwright_client import browser_page
    print(f"\nLoading: {args.url}")
    with browser_page("sephora", args.url) as page:
        try:
            page.wait_for_selector("[data-at='order_status']", timeout=10000)
            print("  [data-at='order_status'] found — SPA rendered OK")
        except Exception:
            print("  WARNING: [data-at='order_status'] not found after 10s")
        html = page.content()

soup = BeautifulSoup(html, "html.parser")

# Print the raw text of every data-at element relevant to delivery
print("\n--- data-at elements found ---")
for attr in ["order_status", "order_date", "estimated_delivery", "delivery_date", "tracking_number"]:
    el = soup.select_one(f"[data-at='{attr}']")
    print(f"  [data-at='{attr}']:  {el.get_text(' ', strip=True)!r}" if el else f"  [data-at='{attr}']:  NOT FOUND")

# Print all data-at attributes present on the page so we can see what's available
print("\n--- all data-at values on page ---")
all_data_at = {el.get("data-at") for el in soup.select("[data-at]")}
for val in sorted(all_data_at):
    print(f"  {val}")

# Run the actual parser and show what it returns
print("\n--- parse_sephora_delivery_html result ---")
try:
    result = parse_sephora_delivery_html(html)
    print(f"  order_status:       {result.order_status}")
    print(f"  estimated_delivery: {result.estimated_delivery}")
    print(f"  tracking_number:    {result.tracking_number}")
    print(f"  carrier:            {result.carrier}")
    print(f"  carrier_status_raw: {result.carrier_status_raw!r}")
except Exception as e:
    print(f"  ERROR: {e}")
