import { api } from "../lib/api-client.js";
import { isAuthenticated } from "../lib/auth.js";

function normalizeRetailer(value) {
  return String(value || "").trim().toLowerCase();
}

function parseCapturedDate(value, fallback) {
  const parsed = new Date(value || fallback || Date.now());
  if (Number.isNaN(parsed.getTime())) {
    return new Date().toISOString();
  }
  return parsed.toISOString();
}

function buildFallbackProductUrl(retailer, item, sourceUrl) {
  if (item?.productUrl) {
    return item.productUrl;
  }

  if (retailer === "nike" && item?.productId) {
    return `https://www.nike.com/t/${item.productId}`;
  }

  if (retailer === "sephora" && item?.productId) {
    return `https://www.sephora.com/product/aftercart-captured-P${item.productId}`;
  }

  return sourceUrl || "";
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "ORDERS_CAPTURED") {
    handleOrdersCaptured(msg.payload)
      .then((res) => sendResponse({ ok: true, data: res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
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

  if (msg.type === "GET_SAVINGS") {
    api.get("/savings/summary")
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }
<<<<<<< Updated upstream
=======

  return false;
>>>>>>> Stashed changes
});

function buildProductUrl(retailer, productId) {
  if (!productId) return null;
  if (retailer === "nike") return `https://www.nike.com/t/product/${productId}`;
  if (retailer === "sephora") return `https://www.sephora.com/product/product-P${productId}`;
  return null;
}

async function handleOrdersCaptured(payload) {
<<<<<<< Updated upstream
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
      order_url: order.orderUrl || null,
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
=======
  const retailer = normalizeRetailer(payload?.retailer);
  const orders = Array.isArray(payload?.orders) ? payload.orders : [];
  const sourceUrl = payload?.sourceUrl || "";
  const capturedAt = parseCapturedDate(payload?.capturedAt, sourceUrl);

  if (!retailer) {
    throw new Error("Captured order payload is missing retailer metadata");
>>>>>>> Stashed changes
  }

  if (orders.length === 0) {
    throw new Error("Captured order payload does not contain any orders");
  }

  const results = [];
  try {
    for (const order of orders) {
      const items = Array.isArray(order.items) ? order.items : [];
      const subtotal = Number(order.total);
      const safeSubtotal = Number.isFinite(subtotal) ? subtotal : 0;
      const perItemPrice = safeSubtotal / (items.length || 1);

      const body = {
        retailer,
        retailer_order_id: order.externalOrderId,
        subtotal: safeSubtotal,
        currency: order.currency || "USD",
        order_date: parseCapturedDate(order.orderDate, capturedAt),
        order_status: "pending",
        order_url: sourceUrl || null,
        raw_capture: {
          retailer,
          captured_at: capturedAt,
          source_url: sourceUrl || null,
          order,
        },
        items: items.map((item) => ({
          product_name: item.name,
          product_url: buildFallbackProductUrl(retailer, item, sourceUrl),
          sku: item.productId || null,
          image_url: item.imageUrl || null,
          paid_price: Number.isFinite(Number(item.paidPrice))
            ? Number(item.paidPrice)
            : perItemPrice,
        })),
      };

      const result = await api.post("/orders", body);
      results.push(result);
    }
  } catch (error) {
    console.warn("[AfterCart] Failed to sync captured orders.", {
      retailer,
      sourceUrl,
      error: error.message,
    });
    throw error;
  }

  console.info("[AfterCart] Synced captured orders to backend.", {
    retailer,
    orderCount: results.length,
  });
  return results;
}

async function handlePriceCaptured(payload) {
  const retailer = normalizeRetailer(payload?.retailer);
  const scrapedPrice = Number(payload?.price);

  if (!retailer) {
    throw new Error("Captured price payload is missing retailer metadata");
  }

  if (!Number.isFinite(scrapedPrice) || scrapedPrice <= 0) {
    throw new Error("Captured price payload is missing a valid price");
  }

  const body = {
    retailer,
    product_id: payload?.productId || null,
    product_name: payload?.productName || null,
    product_url: payload?.sourceUrl || null,
    source_url: payload?.sourceUrl || null,
    scraped_price: scrapedPrice,
    currency: payload?.currency || "USD",
    captured_at: parseCapturedDate(payload?.capturedAt, payload?.sourceUrl),
  };

  try {
    const result = await api.post("/prices/captures", body);
    console.info("[AfterCart] Synced captured price to backend.", result);
    return result;
  } catch (error) {
    console.warn("[AfterCart] Failed to sync captured price.", {
      retailer,
      productId: payload?.productId || null,
      sourceUrl: payload?.sourceUrl || null,
      error: error.message,
    });
    throw error;
  }
}

chrome.alarms.create("checkPriceDrops", { periodInMinutes: 60 });
chrome.alarms.create("checkDeliveryStatus", { periodInMinutes: 30 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  const authed = await isAuthenticated();
  if (!authed) {
    return;
  }

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
    } catch (error) {
      console.warn("[AfterCart] Price drop check failed:", error);
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
    } catch (error) {
      console.warn("[AfterCart] Delivery check failed:", error);
    }
  }
});
