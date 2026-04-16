class NikeExtractor extends BaseExtractor {
  constructor() {
    super("nike");
  }

  extractOrders() {
    const orders = [];
    // Nike order history page renders cards for each order
    const orderCards = document.querySelectorAll(
      "[data-testid='order-card'], .order-card, .css-1rynq56"
    );

    for (const card of orderCards) {
      try {
        // Order ID is usually in a heading or data attribute
        const orderId = card.querySelector(
          "[data-testid='order-number'], .order-number"
        )?.textContent?.trim()?.replace(/^#/, "");

        const totalEl = card.querySelector(
          "[data-testid='order-total'], .order-total"
        );
        const totalText = totalEl?.textContent?.trim() || "";
        const total = parseFloat(totalText.replace(/[^0-9.]/g, "")) || 0;

        const dateEl = card.querySelector(
          "[data-testid='order-date'], .order-date, time"
        );
        const orderDate = dateEl?.textContent?.trim() || 
                          dateEl?.getAttribute("datetime") || "";

        // Extract individual items within the order
        const items = [];
        const itemEls = card.querySelectorAll(
          "[data-testid='order-item'], .order-item, .product-card"
        );
        for (const itemEl of itemEls) {
          const name = itemEl.querySelector(
            "[data-testid='product-name'], .product-name, a[href*='/t/']"
          )?.textContent?.trim();

          // Nike style codes appear in product URLs: /t/slug/STYLE_CODE
          const productLink = itemEl.querySelector("a[href*='/t/']");
          const styleCode = productLink?.href?.match(/\/t\/[^/]+\/(\w+)/)?.[1];
          const imgUrl = itemEl.querySelector("img")?.src;

          if (name) {
            items.push({
              name,
              productId: styleCode || null,
              productUrl: productLink?.href || null,
              imageUrl: imgUrl || null,
            });
          }
        }

        // Order detail URL — used by backend for delivery status polling
        const orderLink = card.querySelector(
          "a[href*='/orders/'], a[href*='/order/']"
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
        console.warn("[AfterCart] Failed to parse Nike order card:", e);
      }
    }
    return orders;
  }

  extractCurrentPrice() {
    // Product detail pages: /t/{slug}/{styleCode}
    const styleMatch = window.location.pathname.match(/\/t\/[^/]+\/(\w+)/);
    if (!styleMatch) return null;

    // Nike uses multiple price elements (original + sale)
    const currentPriceEl = document.querySelector(
      "[data-testid='currentPrice-container'], " +
      "[data-testid='product-price-reduced'], " +
      "[data-testid='product-price'], " +
      ".product-price"
    );
    const priceText = currentPriceEl?.textContent?.trim() || "";
    const price = parseFloat(priceText.replace(/[^0-9.]/g, "")) || null;

    const titleEl = document.querySelector(
      "[data-testid='product_title'], h1#pdp_product_title, h1"
    );
    const productName = titleEl?.textContent?.trim() || "";

    if (price) {
      return {
        productId: styleMatch[1],
        productName,
        price,
        currency: "USD",
      };
    }
    return null;
  }
}

// Auto-run on page load
const nikeExtractor = new NikeExtractor();
nikeExtractor.run();
