class TargetExtractor extends BaseExtractor {
  constructor() {
    super("target");
  }

  extractOrders() {
    // TODO: Inspect Target's order history DOM and implement
    // selectors for order cards, IDs, totals, items.
    const orders = [];
    // Example structure:
    // const cards = document.querySelectorAll("[data-test='orderCard']");
    // for (const card of cards) { ... }
    return orders;
  }

  extractCurrentPrice() {
    // TODO: Inspect Target PDP and extract price + product ID
    // const priceEl = document.querySelector("[data-test='product-price']");
    return null;
  }
}

const targetExtractor = new TargetExtractor();
targetExtractor.run();
