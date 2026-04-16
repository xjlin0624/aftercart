class SephoraExtractor extends BaseExtractor {
  constructor() {
    super("sephora");
  }

  extractOrders() {
    const orders = [];
    // Sephora order history cards
    const orderCards = document.querySelectorAll(
      "[data-at='order_card'], [data-comp='OrderCard'], .order-history-card"
    );

    for (const card of orderCards) {
      try {
        const orderId = card.querySelector(
          "[data-at='order_number'], .order-number"
        )?.textContent?.trim()?.replace(/^Order\s*#?\s*/i, "");

        const totalEl = card.querySelector(
          "[data-at='order_total'], .order-total"
        );
        const totalText = totalEl?.textContent?.trim() || "";
        const total = parseFloat(totalText.replace(/[^0-9.]/g, "")) || 0;

        const dateEl = card.querySelector(
          "[data-at='order_date'], .order-date"
        );
        const orderDate = dateEl?.textContent?.trim() || "";

        const items = [];
        const itemEls = card.querySelectorAll(
          "[data-at='order_product'], .order-product, .product-info"
        );
        for (const itemEl of itemEls) {
          const name = itemEl.querySelector(
            "[data-at='product_name'], .product-name, a[href*='/product/']"
          )?.textContent?.trim();

          // Sephora SKU IDs appear in product URLs: /product/{slug}-P{skuId}
          const productLink = itemEl.querySelector("a[href*='/product/']");
          const skuId = productLink?.href?.match(/-P(\d+)/)?.[1];
          const imgUrl = itemEl.querySelector("img")?.src;

          if (name) {
            items.push({
              name,
              productId: skuId || null,
              productUrl: productLink?.href || null,
              imageUrl: imgUrl || null,
            });
          }
        }

        // Order detail URL — used by backend for delivery status polling
        const orderLink = card.querySelector(
          "a[href*='/orders/'], a[href*='/order/'], a[href*='/OrderDetail']"
        );
        const orderUrl = orderLink
          ? new URL(orderLink.href, window.location.origin).toString()
          : null;

        if (orderId) {
          orders.push({
            externalOrderId: orderId,
            orderDate,
            orderUrl,
            total,
            currency: "USD",
            items,
          });
        }
      } catch (e) {
        console.warn("[AfterCart] Failed to parse Sephora order card:", e);
      }
    }
    return orders;
  }

  extractCurrentPrice() {
    // Product detail pages: /product/{slug}-P{skuId}
    const skuMatch = window.location.pathname.match(/-P(\d+)/);
    if (!skuMatch) return null;

    // Sephora shows original price + sale price
    const currentPriceEl = document.querySelector(
      "[data-at='price_sale'], [data-at='price'], " +
      "[data-comp='Price'] b, .css-0"
    );
    const priceText = currentPriceEl?.textContent?.trim() || "";
    const price = parseFloat(priceText.replace(/[^0-9.]/g, "")) || null;

    const titleEl = document.querySelector(
      "[data-at='product_name'], [data-comp='DisplayName'], " +
      "h1 span[data-at='product_name']"
    );
    const brandEl = document.querySelector(
      "[data-at='brand_name'], [data-comp='BrandName']"
    );
    const brand = brandEl?.textContent?.trim() || "";
    const name = titleEl?.textContent?.trim() || "";
    const productName = brand ? `${brand} — ${name}` : name;

    if (price) {
      return {
        productId: skuMatch[1],
        productName,
        price,
        currency: "USD",
      };
    }
    return null;
  }
}

// Auto-run on page load
const sephoraExtractor = new SephoraExtractor();
sephoraExtractor.run();
