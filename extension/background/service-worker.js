import { api } from "../lib/api-client.js";
import { isAuthenticated } from "../lib/auth.js";

// --- Message handler: route content script messages to the API ---
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "ORDERS_CAPTURED") {
    handleOrdersCaptured(msg.payload)
      .then((res) => sendResponse({ ok: true, data: res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true; // keep channel open for async response
  }

  if (msg.type === "PRICE_CAPTURED") {
    handlePriceCaptured(msg.payload)
      .then((res) => sendResponse({ ok: true, data: res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (msg.type === "GET_ORDERS") {
    api.get("/orders")
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (msg.type === "GET_ALERTS") {
    api.get("/alerts")
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }
});

function buildProductUrl(retailer, productId) {
  if (!productId) return null;
  if (retailer === "nike") return `https://www.nike.com/t/product/${productId}`;
  if (retailer === "sephora") return `https://www.sephora.com/product/product-P${productId}`;
  return null;
}

async function handleOrdersCaptured(payload) {
  // POST each order individually to /orders (backend expects a single order)
  const { retailer, orders } = payload;
  const results = [];
  for (const order of orders) {
    const itemCount = order.items?.length || 1;
    const perItemPrice = order.total / itemCount;

    const body = {
      retailer,
      retailer_order_id: order.externalOrderId,
      subtotal: order.total,
      order_date: new Date(order.orderDate).toISOString(),
      order_status: "pending",
      items: (order.items || []).map((item) => ({
        product_name: item.name,
        product_url: item.productUrl || buildProductUrl(retailer, item.productId),
        sku: item.productId,
        image_url: item.imageUrl,
        paid_price: perItemPrice,
      })),
    };

    const res = await api.post("/orders", body);
    results.push(res);
  }
  return results;
}

async function handlePriceCaptured(_payload) {
  // No-op: backend price-snapshot endpoint does not exist yet
  console.log("[AfterCart] handlePriceCaptured — no backend endpoint, skipping.");
}

// --- Alarms: periodic checks ---
chrome.alarms.create("checkPriceDrops", { periodInMinutes: 60 });
chrome.alarms.create("checkDeliveryStatus", { periodInMinutes: 30 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  const authed = await isAuthenticated();
  if (!authed) return;

  if (alarm.name === "checkPriceDrops") {
    try {
      const alerts = await api.get("/alerts?type=price_drop&unread=true");
      if (alerts.length > 0) {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon128.png",
          title: "Price Drop Detected!",
          message: `${alerts.length} item(s) dropped in price. Click to view.`,
        });
      }
    } catch (e) {
      console.warn("[AfterCart] Price drop check failed:", e);
    }
  }

  if (alarm.name === "checkDeliveryStatus") {
    try {
      const alerts = await api.get("/alerts?type=delivery_anomaly&unread=true");
      if (alerts.length > 0) {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon128.png",
          title: "Delivery Alert",
          message: `${alerts.length} delivery issue(s) detected.`,
        });
      }
    } catch (e) {
      console.warn("[AfterCart] Delivery check failed:", e);
    }
  }
});
