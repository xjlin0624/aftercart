/**
 * Base class for retailer-specific order extraction.
 * Subclasses implement extractOrders() and extractCurrentPrice().
 * Sends extracted data to the service worker via chrome.runtime.
 */
class BaseExtractor {
  constructor(retailerName) {
    this.retailer = retailerName;
  }

  /** Override: return array of order objects from the current page */
  extractOrders() {
    throw new Error("extractOrders() not implemented");
  }

  /** Override: return { productId, price, currency } from a product page */
  extractCurrentPrice() {
    return null;
  }

  /** Detect page type and trigger appropriate extraction */
  async run() {
    const url = window.location.href;

    // Attempt order extraction on order-history / order-detail pages
    const orders = this.extractOrders();
    if (orders && orders.length > 0) {
      chrome.runtime.sendMessage({
        type: "ORDERS_CAPTURED",
        payload: {
          retailer: this.retailer,
          orders,
          capturedAt: new Date().toISOString(),
          sourceUrl: url,
        },
      });
    }

    // Attempt price extraction on product pages
    const priceData = this.extractCurrentPrice();
    if (priceData) {
      chrome.runtime.sendMessage({
        type: "PRICE_CAPTURED",
        payload: {
          retailer: this.retailer,
          ...priceData,
          capturedAt: new Date().toISOString(),
          sourceUrl: url,
        },
      });
    }
  }
}
