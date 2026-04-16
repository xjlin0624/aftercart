import { getApiBaseUrl, setApiBaseUrl } from "../lib/api-client.js";
import { login, logout } from "../lib/auth.js";

document.addEventListener("DOMContentLoaded", async () => {
  const loginView = document.getElementById("login-view");
  const mainView = document.getElementById("main-view");
  const loginButton = document.getElementById("login-btn");
  const logoutButton = document.getElementById("logout-btn");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const apiBaseInput = document.getElementById("api-base-url");
  const errorEl = document.getElementById("login-error");

  apiBaseInput.value = await getApiBaseUrl();

  const { authToken } = await chrome.storage.local.get("authToken");
  if (authToken) {
    showMain();
  }

  loginButton.addEventListener("click", async () => {
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    try {
      errorEl.classList.add("hidden");
      apiBaseInput.value = await setApiBaseUrl(apiBaseInput.value);
      await login(email, password);
      showMain();
    } catch (e) {
      errorEl.textContent = e.message;
      errorEl.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    await logout();
    mainView.classList.add("hidden");
    loginView.classList.remove("hidden");
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((content) => content.classList.add("hidden"));
      tab.classList.add("active");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.remove("hidden");
    });
  });

  async function showMain() {
    loginView.classList.add("hidden");
    mainView.classList.remove("hidden");
    await Promise.all([loadOrders(), loadAlerts(), loadSavings()]);
  }

  async function loadOrders() {
    const res = await sendToBackground({ type: "GET_ORDERS" });
    const list = document.getElementById("orders-list");
    if (!res.ok || !res.data?.length) return;

    list.innerHTML = "";
    for (const order of res.data) {
      const card = document.createElement("div");
      card.className = "order-card";
      const total = Number(order.subtotal ?? order.total);
      const formattedTotal = Number.isFinite(total) ? `$${total.toFixed(2)}` : "-";

      card.innerHTML = `
        <h3>${order.retailer} - ${order.retailer_order_id}</h3>
        <div class="meta">${order.order_date} | ${formattedTotal}</div>
      `;
      list.appendChild(card);
    }
  }

  async function loadAlerts() {
    const res = await sendToBackground({ type: "GET_ALERTS" });
    const list = document.getElementById("alerts-list");
    if (!res.ok || !res.data?.length) return;

    list.innerHTML = "";
    for (const alert of res.data) {
      const card = document.createElement("div");
      const alertType = alert.alert_type === "price_drop" ? "price-drop" : "delivery";
      card.className = `alert-card ${alertType}`;
      card.innerHTML = `
        <h3>${alert.title}</h3>
        <div class="meta">${alert.body}</div>
      `;
      list.appendChild(card);
    }
  }

  async function loadSavings() {
    try {
      await sendToBackground({ type: "GET_ORDERS" });
      const el = document.getElementById("total-savings");
      el.textContent = "$0.00";
    } catch (_error) {
      // Ignore load failures; the popup can still function for orders and alerts.
    }
  }

  function sendToBackground(msg) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(msg, resolve);
    });
  }
});
