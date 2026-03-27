document.addEventListener("DOMContentLoaded", async () => {
  const loginView = document.getElementById("login-view");
  const mainView  = document.getElementById("main-view");

  // Check auth state
  const { authToken } = await chrome.storage.local.get("authToken");
  if (authToken) {
    showMain();
  }

  // --- Login ---
  document.getElementById("login-btn").addEventListener("click", async () => {
    const email    = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const errorEl  = document.getElementById("login-error");

    try {
      errorEl.classList.add("hidden");
      const res = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error("Invalid credentials");

      const { access_token, user } = await res.json();
      await chrome.storage.local.set({ authToken: access_token, user });
      showMain();
    } catch (e) {
      errorEl.textContent = e.message;
      errorEl.classList.remove("hidden");
    }
  });

  // --- Logout ---
  document.getElementById("logout-btn").addEventListener("click", async () => {
    await chrome.storage.local.remove(["authToken", "user"]);
    mainView.classList.add("hidden");
    loginView.classList.remove("hidden");
  });

  // --- Tab switching ---
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.add("hidden"));
      tab.classList.add("active");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.remove("hidden");
    });
  });

  // --- Load data into main view ---
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
      card.innerHTML = `
        <h3>${order.retailer} — ${order.retailer_order_id}</h3>
        <div class="meta">${order.order_date} · $${order.total?.toFixed(2) || "—"}</div>
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
      const res = await sendToBackground({ type: "GET_ORDERS" });
      const el = document.getElementById("total-savings");
      el.textContent = "$0.00"; // TODO: wire to real savings API
    } catch (e) { /* ignore */ }
  }

  function sendToBackground(msg) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(msg, resolve);
    });
  }
});
