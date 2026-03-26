const API_BASE = "/api";
const TOKEN_KEY = "aftercart_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function authHeaders() {
  const token = getToken();
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

async function handleResponse(res) {
  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const message =
      (isJson && (data.detail || data.message || data.error)) ||
      `Request failed: ${res.status}`;
    throw new Error(message);
  }

  return data;
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  const data = await handleResponse(res);

  const token =
    data.access_token || data.token || data.jwt || data.accessToken || null;

  if (token) {
    setToken(token);
  }

  return data;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function getOrders() {
  const res = await fetch(`${API_BASE}/orders`, {
    method: "GET",
    headers: {
      ...authHeaders(),
    },
  });

  return handleResponse(res);
}

export async function getAlerts(status) {
  const url = new URL(`${window.location.origin}${API_BASE}/alerts`);
  if (status) {
    url.searchParams.set("status", status);
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      ...authHeaders(),
    },
  });

  return handleResponse(res);
}

export async function resolveAlert(id) {
  const res = await fetch(`${API_BASE}/alerts/${id}/resolve`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
  });

  return handleResponse(res);
}

export async function dismissAlert(id) {
  const res = await fetch(`${API_BASE}/alerts/${id}/dismiss`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
  });

  return handleResponse(res);
}