import { getApiBaseUrl, setApiBaseUrl } from "../lib/api-client.js";
import { login, logout } from "../lib/auth.js";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

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
      await showMain();
    } catch (error) {
      errorEl.textContent = error.message;
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
    const list = document.getElementById("orders-list");
    const res = await sendToBackground({ type: "GET_ORDERS" });

    if (!res?.ok) {
      list.innerHTML = `<p class="empty-state">${res?.error || "Unable to load orders."}</p>`;
      return;
    }

    if (!res.data?.length) {
      list.innerHTML = `
        <p class="empty-state">
          Visit a supported retailer order page to capture your first order.
        </p>
      `;
      return;
    }

    list.innerHTML = "";
    for (const order of res.data) {
      const card = document.createElement("div");
      card.className = "order-card";
      const total = Number(order.subtotal ?? order.total);
      const formattedTotal = Number.isFinite(total) ? currencyFormatter.format(total) : "-";

      card.innerHTML = `
        <h3>${order.retailer} - ${order.retailer_order_id}</h3>
        <div class="meta">${order.order_date} | ${formattedTotal}</div>
      `;
      list.appendChild(card);
    }
  }

  async function loadAlerts() {
    const list = document.getElementById("alerts-list");
    const res = await sendToBackground({ type: "GET_ALERTS" });

    if (!res?.ok) {
      list.innerHTML = `<p class="empty-state">${res?.error || "Unable to load alerts."}</p>`;
      return;
    }

    if (!res.data?.length) {
      list.innerHTML = `<p class="empty-state">No alerts yet.</p>`;
      return;
    }

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
    const totalEl = document.getElementById("total-savings");
    const detailEl = document.getElementById("savings-detail");
    const breakdownEl = document.getElementById("savings-breakdown");

    totalEl.textContent = "Loading...";
    detailEl.textContent = "Fetching your latest backend savings summary.";
    breakdownEl.innerHTML = "";

    const res = await sendToBackground({ type: "GET_SAVINGS" });
    if (!res?.ok) {
      totalEl.textContent = "Unavailable";
      detailEl.textContent = res?.error || "Unable to load savings right now.";
      return;
    }

    const totalRecovered = Number(res.data?.total_recovered || 0);
    const totalActions = Number(res.data?.total_actions || 0);
    const successfulActions = Number(res.data?.successful_actions || 0);
    const byAction = Array.isArray(res.data?.by_action) ? res.data.by_action : [];

    totalEl.textContent = currencyFormatter.format(totalRecovered);

    if (totalActions === 0) {
      detailEl.textContent =
        "No recovered savings logged yet. Savings appear here after you act on an alert.";
      return;
    }

    detailEl.textContent = `${successfulActions} successful action(s) across ${totalActions} logged outcome(s).`;

    if (byAction.length > 0) {
      breakdownEl.innerHTML = byAction
        .map(
          (entry) => `
            <div class="breakdown-item">
              <span>${entry.action_taken.replace(/_/g, " ")}</span>
              <strong>${currencyFormatter.format(Number(entry.total_recovered || 0))}</strong>
            </div>
          `
        )
        .join("");
    }
  }

  function sendToBackground(msg) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(msg, (response) => {
        resolve(response || { ok: false, error: "No response from extension background." });
      });
    });
  }
});
