import re

from ..models.enums import OrderStatus
from .base import DeliveryCheckResult, PriceCheckResult, RetailerPriceAdapter
from .common import detect_order_status, extract_json_ld_price, extract_meta_price, extract_price_from_selectors, make_soup, page_requires_authentication, parse_date_from_text
from .exceptions import RetailerNotReadyError, ScraperTransientError
from .playwright_client import browser_page
from .reliability import run_scrape_with_guards


_SEPHORA_PRICE_SELECTORS = [
    "[data-at='price']",
    "[data-comp='PriceInfo']",
    ".css-1jczs19",
]

_SEPHORA_ETA_RE = re.compile(r"(?:Estimated delivery|Arrives|Delivery by)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{1,2}(?:,\s+\d{4})?)", re.IGNORECASE)


def parse_sephora_price_html(html: str, *, source_url: str | None = None) -> PriceCheckResult:
    soup = make_soup(html)
    price = (
        extract_price_from_selectors(soup, _SEPHORA_PRICE_SELECTORS)
        or extract_meta_price(soup)
        or extract_json_ld_price(soup)
    )
    if price is None:
        raise ScraperTransientError("Sephora price not found on page.")

    # If a price was successfully extracted, treat the product as available.
    # Sephora pages contain "Out of Stock" text for individual shades/sizes
    # even when other variants are available, causing false negatives.
    return PriceCheckResult(
        scraped_price=price,
        currency="USD",
        is_available=True,
        raw_payload={"retailer": "sephora"},
        source_url=source_url,
    )


_SEPHORA_STATUS_MAP = {
    "delivered": OrderStatus.delivered,
    "order delivered": OrderStatus.delivered,
    "delivery complete": OrderStatus.delivered,
    "order complete": OrderStatus.delivered,
    "in transit": OrderStatus.in_transit,
    "on the way": OrderStatus.in_transit,
    "out for delivery": OrderStatus.in_transit,
    "shipped": OrderStatus.shipped,
    "partially shipped": OrderStatus.shipped,
    "processing": OrderStatus.shipped,
    "cancelled": OrderStatus.cancelled,
    "canceled": OrderStatus.cancelled,
    "returned": OrderStatus.returned,
    "pending": OrderStatus.pending,
    "order placed": OrderStatus.pending,
}


def _parse_sephora_status(text: str) -> OrderStatus | None:
    lowered = text.lower().strip()
    # Exact match first
    if lowered in _SEPHORA_STATUS_MAP:
        return _SEPHORA_STATUS_MAP[lowered]
    # Substring match
    for phrase, status in _SEPHORA_STATUS_MAP.items():
        if phrase in lowered:
            return status
    return None


def parse_sephora_delivery_html(html: str) -> DeliveryCheckResult:
    soup = make_soup(html)
    page_text = soup.get_text(" ", strip=True)
    if page_requires_authentication(page_text):
        raise RetailerNotReadyError("Sephora delivery scraping requires an authenticated session.")

    # Use data-at attributes from Sephora's React DOM (same selectors as the extension)
    status_el = soup.select_one("[data-at='order_status']")
    status_text = status_el.get_text(" ", strip=True) if status_el else ""
    order_status = _parse_sephora_status(status_text) or detect_order_status(status_text or page_text)

    # ETA — Sephora renders "Delivery By" as a plain h4 with no data-at inside shipment_section
    estimated_delivery = None
    shipment_section = soup.select_one("[data-at='shipment_section']")
    if shipment_section:
        for h4 in shipment_section.find_all("h4"):
            if "delivery by" in h4.get_text(strip=True).lower():
                # Date is a bare text node directly after the h4 inside the same div
                parent_div = h4.parent
                if parent_div:
                    text_node = "".join(
                        str(s).strip() for s in parent_div.strings if str(s).strip() and str(s).strip() != h4.get_text(strip=True)
                    )
                    # Strip leading weekday abbreviation e.g. "Fri, Jun 28" -> "Jun 28"
                    text_node = re.sub(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*", "", text_node, flags=re.IGNORECASE)
                    estimated_delivery = parse_date_from_text(text_node)
                break
    if estimated_delivery is None:
        eta_match = _SEPHORA_ETA_RE.search(page_text)
        estimated_delivery = parse_date_from_text(eta_match.group(1)) if eta_match else None

    # Tracking number and carrier — extracted from the ship.sephora.com tracking link href
    tracking_number = None
    carrier = None
    tracking_link = soup.select_one("[data-at='shipment_section'] a[href*='ship.sephora.com']")
    if tracking_link:
        href = tracking_link.get("href", "")
        tn_match = re.search(r"tracking_numbers=([A-Z0-9]+)", href)
        if tn_match:
            tracking_number = tn_match.group(1)
        carrier_match_href = re.search(r"/tracking/sephora/([a-z]+)", href, re.IGNORECASE)
        if carrier_match_href:
            carrier = carrier_match_href.group(1).upper()

    carrier_match = re.search(r"(UPS|FedEx|USPS|OnTrac|LaserShip)", page_text, re.IGNORECASE)
    if not carrier:
        carrier = carrier_match.group(1) if carrier_match else None

    return DeliveryCheckResult(
        order_status=order_status,
        estimated_delivery=estimated_delivery,
        tracking_number=tracking_number,
        carrier=carrier,
        carrier_status_raw=status_el.get_text(" ", strip=True) if status_el else page_text[:240],
        raw_payload={"retailer": "sephora"},
    )


class SephoraAdapter(RetailerPriceAdapter):
    retailer = "sephora"

    def fetch_current_price(self, order_item) -> PriceCheckResult:
        def scrape() -> PriceCheckResult:
            with browser_page(self.retailer, order_item.product_url) as page:
                return parse_sephora_price_html(page.content(), source_url=order_item.product_url)

        return run_scrape_with_guards(self.retailer, "price_check", scrape)

    def fetch_delivery_status(self, order) -> DeliveryCheckResult:
        if not order.order_url:
            raise RetailerNotReadyError("Sephora delivery polling requires order_url.")

        def scrape() -> DeliveryCheckResult:
            with browser_page(self.retailer, order.order_url) as page:
                # Wait for Sephora's SPA to render the order status element
                try:
                    page.wait_for_selector("[data-at='order_status']", timeout=10000)
                except Exception:
                    pass  # Fall through — parse whatever rendered
                return parse_sephora_delivery_html(page.content())

        return run_scrape_with_guards(self.retailer, "delivery_check", scrape)
