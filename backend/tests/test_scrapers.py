from backend.app.models.enums import OrderStatus
from backend.app.scrapers import (
    parse_amazon_price_html,
    parse_nike_delivery_html,
    parse_nike_price_html,
    parse_sephora_delivery_html,
    parse_sephora_price_html,
)


def test_parse_nike_price_html_prefers_meta_price():
    html = """
    <html>
      <head><meta property="product:price:amount" content="129.99"></head>
      <body><div data-testid="product-price">$140.00</div></body>
    </html>
    """

    result = parse_nike_price_html(html, source_url="https://nike.test/product")

    assert result.scraped_price == 129.99
    assert result.source_url == "https://nike.test/product"


def test_parse_sephora_price_html_from_visible_price():
    html = """
    <html>
      <body>
        <div data-at="price">$49.00</div>
      </body>
    </html>
    """

    result = parse_sephora_price_html(html)

    assert result.scraped_price == 49.00
    assert result.is_available is True


def test_parse_amazon_price_html_from_standard_selector():
    html = """
    <html>
      <body>
        <span class="a-price"><span class="a-offscreen">$22.49</span></span>
      </body>
    </html>
    """

    result = parse_amazon_price_html(html)

    assert result.scraped_price == 22.49


def test_parse_nike_delivery_html_extracts_status_eta_and_tracking():
    html = """
    <html>
      <body>
        <div>In Transit</div>
        <div>Estimated delivery: March 22, 2026</div>
        <div>Tracking Number: 1Z999AA10123456784</div>
      </body>
    </html>
    """

    result = parse_nike_delivery_html(html)

    assert result.order_status == OrderStatus.in_transit
    assert str(result.estimated_delivery) == "2026-03-22"
    assert result.tracking_number == "1Z999AA10123456784"


def test_parse_sephora_delivery_html_extracts_carrier():
    html = """
    <html>
      <body>
        <div>Delivered</div>
        <div>Delivery by Mar 20, 2026</div>
        <div>Carrier: UPS</div>
      </body>
    </html>
    """

    result = parse_sephora_delivery_html(html)

    assert result.order_status == OrderStatus.delivered
    assert result.carrier == "UPS"
