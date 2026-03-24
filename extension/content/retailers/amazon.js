class AmazonExtractor extends BaseExtractor {
  constructor() {
    super("amazon");
  }

  extractOrders() {
    const orders = [];
    // Target the order cards on /gp/your-account/order-history
    const orderCards = document.querySelectorAll(".order-card, .a-box-group.order");
    
    for (const card of orderCards) {
      try {
        const orderId = card.querySelector(
          "[data-order-id], .yohtmlc-order-id .value"
        )?.textContent?.trim();

        const totalEl = card.querySelector(
          ".yohtmlc-order-total .value, .a-color-price"
        );
        const totalText = totalEl?.textContent?.trim() || "";
        const total = parseFloat(totalText.replace(/[^0-9.]/g, "")) || 0;

        const dateEl = card.querySelector(
          ".yohtmlc-order-date .value, [data-testid='order-date']"
        );
        const orderDate = dateEl?.textContent?.trim() || "";

        // Extract individual items within the order
        const items = [];
        const itemEls = card.querySelectorAll(
          ".yohtmlc-item, .a-fixed-left-grid-inner"
        );
        for (const itemEl of itemEls) {
          const name = itemEl.querySelector(
            ".yohtmlc-product-title, a[href*='/dp/']"
          )?.textContent?.trim();
          const asin = itemEl.querySelector("a[href*='/dp/']")
            ?.href?.match(/\/dp\/(\w+)/)?.[1];
          const imgUrl = itemEl.querySelector("img")?.src;

          if (name) {
            items.push({
              name,
              productId: asin || null,
              imageUrl: imgUrl || null,
            });
          }
        }

        if (orderId) {
          orders.push({
            externalOrderId: orderId,
            orderDate,
            total,
            currency: "USD",
            items,
          });
        }
      } catch (e) {
        console.warn("[AfterCart] Failed to parse order card:", e);
      }
    }
    return orders;
  }

  extractCurrentPrice() {
    // Product detail pages (/dp/ASIN)
    const asinMatch = window.location.pathname.match(/\/dp\/(\w+)/);
    if (!asinMatch) return null;

    const priceEl = document.querySelector(
      "#priceblock_ourprice, #priceblock_dealprice, .a-price .a-offscreen"
    );
    const priceText = priceEl?.textContent?.trim() || "";
    const price = parseFloat(priceText.replace(/[^0-9.]/g, "")) || null;

    const titleEl = document.querySelector("#productTitle");
    const productName = titleEl?.textContent?.trim() || "";

    if (price) {
      return {
        productId: asinMatch[1],
        productName,
        price,
        currency: "USD",
      };
    }
    return null;
  }
}

// Auto-run on page load
const extractor = new AmazonExtractor();
extractor.run();
