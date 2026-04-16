const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
const TOKEN_KEY = "aftercart_token";
const REFRESH_KEY = "aftercart_refresh_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

function setTokens(access, refresh) {
  localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function createApiUrl(path, params = {}) {
  const base = API_BASE.startsWith("http")
    ? API_BASE
    : `${window.location.origin}${API_BASE}`;
  const normalizedBase = base.endsWith("/") ? base : `${base}/`;
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;
  const url = new URL(normalizedPath, normalizedBase);

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    url.searchParams.set(key, String(value));
  });

  return url.toString();
}

async function handleResponse(res) {
  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const message =
      (isJson && (data.detail || data.message || data.error)) ||
      `Request failed: ${res.status}`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  return data;
}

// Attempt to refresh tokens. Returns true on success, false on failure.
let _refreshing = null;
async function attemptTokenRefresh() {
  // Deduplicate concurrent refresh attempts
  if (_refreshing) return _refreshing;

  _refreshing = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) {
      clearTokens();
      return false;
    }

    try {
      const res = await fetch(createApiUrl("auth/refresh"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });

      if (!res.ok) {
        clearTokens();
        return false;
      }

      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      clearTokens();
      return false;
    } finally {
      _refreshing = null;
    }
  })();

  return _refreshing;
}

// Fetch wrapper: on 401, refresh once and retry. On second failure, force logout.
async function apiFetch(url, options = {}) {
  const res = await fetch(url, options);

  if (res.status !== 401) return res;

  const refreshed = await attemptTokenRefresh();
  if (!refreshed) {
    window.dispatchEvent(new window.Event("aftercart:logout"));
    // Return the original 401 so callers get a proper error
    return res;
  }

  // Retry with the new access token
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${getToken()}`,
    },
  });
}

export async function signup(email, password, displayName) {
  const res = await fetch(createApiUrl("auth/signup"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName || undefined }),
  });
  return handleResponse(res);
}

export async function login(email, password) {
  const res = await fetch(createApiUrl("auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await handleResponse(res);
  const access = data.access_token || data.token || data.jwt || data.accessToken || null;
  if (access) setTokens(access, data.refresh_token || null);
  return data;
}

export async function logout() {
  const refresh = getRefreshToken();
  if (refresh) {
    // Fire-and-forget — invalidates the token server-side
    fetch(createApiUrl("auth/logout"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    }).catch(() => {});
  }
  clearTokens();
}

export async function getOrders() {
  const res = await apiFetch(createApiUrl("orders"), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getAlerts(statusOrFilters) {
  const params =
    typeof statusOrFilters === "string"
      ? { status: statusOrFilters }
      : statusOrFilters || {};
  const res = await apiFetch(createApiUrl("alerts", params), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function createAlert(payload) {
  const res = await apiFetch(createApiUrl("alerts"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function resolveAlert(id) {
  const res = await apiFetch(createApiUrl(`alerts/${id}/resolve`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  return handleResponse(res);
}

export async function dismissAlert(id) {
  const res = await apiFetch(createApiUrl(`alerts/${id}/dismiss`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getPreferences() {
  const res = await apiFetch(createApiUrl("users/me/preferences"), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function updatePreferences(payload) {
  const res = await apiFetch(createApiUrl("users/me/preferences"), {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function registerPushToken(payload) {
  const res = await apiFetch(createApiUrl("push/tokens"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function unregisterPushToken(token) {
  const res = await apiFetch(createApiUrl(`push/tokens/${encodeURIComponent(token)}`), {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getSelf() {
  const res = await apiFetch(createApiUrl("users/me"), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getSavingsSummary(limit) {
  const res = await apiFetch(createApiUrl("savings/summary", limit ? { limit } : {}), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getSubscriptions() {
  const res = await apiFetch(createApiUrl("subscriptions"), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getPriceHistory(itemId, limit) {
  const res = await apiFetch(createApiUrl(`prices/${itemId}/history`, limit ? { limit } : {}), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getAlertRecommendation(alertId) {
  const res = await apiFetch(createApiUrl(`alerts/${alertId}/recommendation`), {
    headers: { ...authHeaders() },
  });
  return handleResponse(res);
}

export async function getAlertMessage(alertId, tone) {
  const res = await apiFetch(
    createApiUrl(`alerts/${alertId}/message`, tone ? { tone } : {}),
    { headers: { ...authHeaders() } }
  );
  return handleResponse(res);
}

export async function logOutcome(payload) {
  const res = await apiFetch(createApiUrl("outcomes"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}
