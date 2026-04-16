import re

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


def parse_sephora_delivery_html(html: str) -> DeliveryCheckResult:
    soup = make_soup(html)
    page_text = soup.get_text(" ", strip=True)
    if page_requires_authentication(page_text):
        raise RetailerNotReadyError("Sephora delivery scraping requires an authenticated session.")

    eta_match = _SEPHORA_ETA_RE.search(page_text)
    estimated_delivery = parse_date_from_text(eta_match.group(1)) if eta_match else None
    order_status = detect_order_status(page_text)
    tracking_match = re.search(r"Tracking(?: number)?\s*[:#]?\s*([A-Z0-9\-]+)", page_text, re.IGNORECASE)
    carrier_match = re.search(r"(UPS|FedEx|USPS|OnTrac|LaserShip)", page_text, re.IGNORECASE)

    return DeliveryCheckResult(
        order_status=order_status,
        estimated_delivery=estimated_delivery,
        tracking_number=tracking_match.group(1) if tracking_match else None,
        carrier=carrier_match.group(1) if carrier_match else None,
        carrier_status_raw=page_text[:240],
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
                return parse_sephora_delivery_html(page.content())

        return run_scrape_with_guards(self.retailer, "delivery_check", scrape)
