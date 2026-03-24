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

async function handleOrdersCaptured(payload) {
  // POST captured orders to backend for de-duplication (FR-4)
  // and storage in centralized order view (FR-5)
  return api.post("/orders/capture", payload);
}

async function handlePriceCaptured(payload) {
  // POST price snapshot to backend for price history (FR-6)
  return api.post("/prices/snapshot", payload);
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
